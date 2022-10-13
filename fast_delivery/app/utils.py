import re
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from minio import Minio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from app.db.models import DadataCleanModel
from app.env import SETTINGS
from app.exceptions import CityNotDefinedException
from app.settings.consts import (
    COOKIE_SCREENSHOT_DIR,
)
from app.settings.log import logger


def extract_passport_ser_num(passport: str) -> (str, str):
    if passport and len(passport) == 10:
        return passport[:4], passport[4:]

    return "", ""


def is_similar_day(dt):
    today = datetime.now()
    return today.year == dt.year and today.day == dt.day and today.month == dt.month


def format_phone(phone: str) -> str:
    """
    форматирует телефон: код страны (для России +7) и сам номер (10 и более цифр)
    Если указан телефон без "8" или "+7", просто возвращает его
    >> format_phone('89119809115 или офис 245 09 79')
    '+79119809115'
    >> format_phone('+79277855504')
    '+79277855504'
    >> format_phone('')
    ''
    >> format_phone('89500393570, 88122400789')
    '+79500393570'
    """
    # может быть указано несколько телефонов, выбираем первый
    phones = re.split(r",| ", phone)
    if len(phones) > 1:
        phone = phones[0]

    # отрабсываем скобки, плюсы и тп
    phone = "".join(e for e in phone if e.isdigit())
    # есть мобильный номер начинается с "8", то обрезаем его b заменяем на "+7"
    if len(phone) == 11 and phone[0] in ["8", "7"]:
        phone = phone[1:]
        phone = "+7" + phone

    return phone


async def get_dadata_city_name(dadata_d: DadataCleanModel, raise_exc=True):
    def _raise_ex():
        if raise_exc:
            logger.error(
                f"Не удалось получить город из объекта: {dadata_d}", exc_info=True
            )
            raise CityNotDefinedException("Не удалось получить город для запроса")
        return None

    if not dadata_d:
        return _raise_ex()

    # проверка на город. Для Мск и Питера
    if dadata_d.region_type == "г":
        city_name = dadata_d.region
    else:
        if dadata_d.city is not None:
            city_name = dadata_d.city
        elif dadata_d.settlement is not None:
            city_name = dadata_d.settlement
        elif dadata_d.area_type == "г" and dadata_d.area is not None:
            city_name = dadata_d.area
        else:
            return _raise_ex()

    return city_name


async def get_terminal_geo(tk_mongo_coll, dadata_d):
    from app.db import DBS

    mng = DBS["mongo_delivery_lists"]["client"]
    if not (dadata_d.geo_lon and dadata_d.geo_lat):
        logger.warning(
            f"Нет координат адреса получателя. Адрес '{dadata_d.source}' определился как '{dadata_d.result}'"
        )
        return
    lon_lat = [dadata_d.geo_lon, dadata_d.geo_lat]
    tk_terminal = await mng[tk_mongo_coll].find_one(
        {
            "loc": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": lon_lat},
                    "$maxDistance": 10000,
                    "$minDistance": 0,
                }
            }
        },
        # {"_id": 1},
    )
    if tk_terminal:
        logger.info(
            f"Терминал {tk_mongo_coll} найден по координатам: {lon_lat}. tk uid: {tk_terminal['_id']} "
            f"Адрес '{dadata_d.source}' определился как '{dadata_d.result}'"
        )
        return tk_terminal

    logger.warning(
        f"Терминал {tk_mongo_coll} не найден по координатам: {lon_lat}. "
        f"Адрес '{dadata_d.source}' определился как '{dadata_d.result}'"
    )


def create_selenium_driver():
    logger.debug("Chrome driver creating..")
    chrome_options = Options()

    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--verbose")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-dev-shm-usage")

    def enable_download_headless(browser):
        browser.command_executor._commands["send_command"] = (
            "POST",
            "/session/$sessionId/chromium/send_command",
        )
        params = {
            "cmd": "Page.setDownloadBehavior",
            "params": {"behavior": "allow", "downloadPath": "./data/"},
        }
        browser.execute("send_command", params)

    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    enable_download_headless(driver)
    return driver


def delete_none(_dict):
    for key, value in list(_dict.items()):
        if isinstance(value, dict):
            delete_none(value)
        elif value is None:
            _dict.pop(key)
    return _dict


def get_screenshot_path(pattern: str, folder: Path = COOKIE_SCREENSHOT_DIR, limit=10):
    l = list(folder.glob(pattern))
    l = sorted(l, key=lambda x: x.name)
    for a in l[: max(0, len(l) - limit + 1)]:
        logger.info(
            f'В папке со скрипшотами больше {limit} файлов с паттерном "{pattern}". Удаляем: {a.absolute()}'
        )
        a.unlink()
    res = folder / pattern.replace(
        "*", str(datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))
    )
    logger.info(f"Путь к сохраненному скриншоту: {res}")
    return res


class TaskScheduler:
    def __init__(self, start_time: str):
        self.start_time = start_time
        now = datetime.now()
        self.parsed_time = parsed_time = datetime.strptime(start_time, "%H:%M")
        self.start_date = datetime(
            now.year, now.month, now.day, parsed_time.hour, parsed_time.minute
        )
        self.ready = True
        logger.debug(
            f"TaskScheduler: start_time={self.start_time} now={now} start_date={self.start_date}"
        )

    def is_task_ready(self):
        now = datetime.now()
        if self.ready and self.start_date < now:
            logger.debug(
                f"is_task_ready: start_time={self.start_time} now={now} start_date={self.start_date}"
            )
            now = now + timedelta(days=1)
            self.start_date = datetime(
                now.year,
                now.month,
                now.day,
                self.parsed_time.hour,
                self.parsed_time.minute,
            )
            self.ready = False
            return True
        return False

    def task_finished(self):
        self.ready = True


def save_df(df, data_name):
    """
    Сохранить pandas Dataframe в S3 с именем data_name
    """
    f = BytesIO()
    df.to_excel(f)
    f.seek(0)
    _client = Minio(
        SETTINGS.S3_AUTH["host"],
        access_key=SETTINGS.S3_AUTH["access_key"],
        secret_key=SETTINGS.S3_AUTH["secret_key"],
        secure=True,
        region="fr",
    )

    _client.put_object(
        bucket_name=SETTINGS.S3_AUTH["bucket"],
        object_name=data_name,
        data=f,
        length=f.getbuffer().nbytes,
        content_type="application/octet-stream",
    )
