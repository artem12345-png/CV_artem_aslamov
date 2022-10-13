import asyncio
import io
from datetime import datetime, timedelta

import httpx
from PyPDF3 import PdfFileMerger, PdfFileReader, PdfFileWriter
from pyppeteer import launch
from pyppeteer.errors import TimeoutError
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.db import DBS
from app.exceptions import NoCookieException
from app.routes.skiff.consts import COOKIE_FILE
from app.settings.consts import PUBLIC_DIR, FONT_PATH, COOKIE_DIR, COOKIE_WAIT_SECONDS
from app.settings.log import logger
from app.utils import get_screenshot_path


async def merge_tk_pdf(mode: str, pdf_bytes: list[io.BytesIO], prefix: str):
    merger = PdfFileMerger(strict=False)
    for pdf_io in pdf_bytes:
        merger.append(pdf_io)

    datestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"{prefix}_{mode}_{datestamp}.pdf"  # задаем имя файла
    with open(PUBLIC_DIR / file_name, "wb") as output:
        merger.write(output)
    return file_name


def modify_cargo_pdf(pdf_io: io.BytesIO, idmonopolia: int, font_size=36):
    packet = io.BytesIO()
    # create a new PDF with Reportlab
    can = canvas.Canvas(packet, pagesize=letter)
    pdfmetrics.registerFont(TTFont("FreeSans", FONT_PATH))
    can.setFont("FreeSans", font_size)
    can.drawString(8, 8, f"Заказ №{idmonopolia}")
    can.save()

    # move to the beginning of the StringIO buffer
    packet.seek(0)
    new_pdf = PdfFileReader(packet)
    # read your existing PDF
    existing_pdf = PdfFileReader(pdf_io)
    output = PdfFileWriter()
    # add the "watermark" (which is the new pdf) on the existing page
    page = existing_pdf.getPage(0)
    page.mergePage(new_pdf.getPage(0))
    output.addPage(page)
    # finally, write "output" to a real file
    output_stream = io.BytesIO()
    output.write(output_stream)
    return output_stream


async def pdf_merge(response, success_orders, prefix):
    if success_orders["orders_with_pdf"]:
        try:
            # формируем файл с заявками
            response.file = await merge_tk_pdf(
                "info", success_orders["pdf_info"], prefix
            )
            # формируем файл с штрих-кодами для грузов
            response.file_cargo = await merge_tk_pdf(
                "cargo", success_orders["pdf_cargo"], prefix
            )
        except Exception as ex:
            logger.exception(
                f"pdf files for orders={success_orders} cant be created with exception message "
                f'"{str(ex)}"'
            )
            response.error = (
                "Заявка создана. "
                "Сервер по обработке pdf в данный момент недоступен. "
                "Вы можете посмотреть файлы в личном кабинете "
            )
    pdf_order_len = len(success_orders["orders_with_pdf"])
    order_len = len(success_orders["orders"])
    if not response.error and pdf_order_len != order_len:
        response.error = f"PDF созданы для {pdf_order_len} заказов из {order_len} успешно созданных. "


class CookiesGetter:
    def __init__(
        self,
        site_name="skiff",
        login_url="https://skif-cargo.ru/login",
        auth=(),
        xpath_login="//input[@placeholder='Email']",
        xpath_pass="//input[@type='password']",
        xpath_button="//button[@type='submit']",
        url_check="https://skif-cargo.ru/getOrders/",
        cookie_file_name=COOKIE_DIR / COOKIE_FILE,
        is_test=False,
    ):
        self.site_name = site_name
        self.login_url = login_url
        self.cookie = {}
        self.auth = auth
        self.xpath_login = xpath_login
        self.xpath_pass = xpath_pass
        self.xpath_button = xpath_button
        self.url_check = url_check
        self.cookie_file = cookie_file_name
        self.is_test = is_test
        self.date = None

    async def is_cookie_valid(self) -> bool:
        if not self.cookie:
            await self.get_cookie_from_db()

        if self.cookie:
            async with httpx.AsyncClient(verify=False, timeout=20) as client:
                res = await client.get(
                    self.url_check,
                    cookies=self.cookie,
                    allow_redirects=False,
                )
                if res.status_code == 200:
                    return True

        self.cookie = {}
        return False

    async def get_cookie_from_db(self):
        fast_delivery_cookies = DBS["mongo_epool_admin"]["client"].get_collection(
            "fast_delivery_cookies"
        )
        field_name = "test" if self.is_test else "prod"
        cookie_record = await fast_delivery_cookies.find_one(
            {"_id": self.site_name}
        )
        if cookie_record and cookie_record.get(field_name):
            self.cookie = cookie_record[field_name]["cookie"]
            self.date = cookie_record[field_name]["date"]

    async def is_cookie_date_valid(self) -> bool:
        coll = DBS["mongo_epool_admin"]["client"].get_collection(
            "fast_delivery_cookies"
        )
        field_name = "test" if self.is_test else "prod"
        if (record := await coll.find_one({"_id": self.site_name})) and record.get(
            field_name
        ):
            date = record[field_name]["date"]
            diff = datetime.now() - date
            return diff < timedelta(days=1)
        else:
            return False

    async def get_cookie(self):
        logger.info(f"Получаем cookie для ЛК {self.site_name}")
        browser = await launch(
            options={"args": ["--no-sandbox"], "ignoreHTTPSErrors": True}
        )
        page = await browser.newPage()
        try:
            await page.goto(self.login_url)

            login_div = await _find_xpath(self.xpath_login, page)
            await login_div.click()
            await login_div.type(self.auth[0])

            await asyncio.sleep(0.5)

            pass_div = await _find_xpath(self.xpath_pass, page)
            await pass_div.click()
            await pass_div.type(self.auth[1])

            submit_btn = await _find_xpath(self.xpath_button, page)
            await page.screenshot(
                options={"path": get_screenshot_path(f"{self.site_name}_fill_*.png")}
            )
            try:
                await asyncio.wait(
                    [
                        submit_btn.click(),
                        page.waitForNavigation(
                            options={"timeout": COOKIE_WAIT_SECONDS * 1_000}
                        ),
                    ]
                )
            except TimeoutError:
                logger.error(
                    f"Получение cookie для {self.site_name} больше таймаута в {COOKIE_WAIT_SECONDS}",
                    exc_info=True,
                )

            await page.screenshot(
                options={"path": get_screenshot_path(f"{self.site_name}_login_*.png")}
            )
            cookies = await page.cookies()
            logger.info(f"Cookie для ЛК {self.site_name}: {cookies}")
            cookies = {cookie["name"]: cookie["value"] for cookie in cookies}
            self.cookie = cookies
            if not cookies or not (await self.is_cookie_valid()):
                self.cookie = {}
                raise NoCookieException("Не были получены куки")

            logger.info(f"Cookie для ЛК {self.site_name} успешно получены")

            field_name = "test" if self.is_test else "prod"
            date_now = datetime.now()
            fast_delivery_cookies = DBS["mongo_epool_admin"]["client"].get_collection(
                "fast_delivery_cookies"
            )
            await fast_delivery_cookies.update_one(
                {"_id": self.site_name},
                {"$set": {field_name: {"cookie": self.cookie, "date": date_now}}},
                upsert=True,
            )
            self.date = date_now

            return cookies
        finally:
            await page.screenshot(
                options={"path": get_screenshot_path(f"{self.site_name}_error_*.png")}
            )
            await browser.close()


async def _find_xpath(xpath, page):
    xpath_divs = await page.xpath(xpath)
    if len(xpath_divs) == 0:
        raise NoCookieException("Не были получены куки")
    logger.info(f"По xpath {xpath} найдено {xpath_divs}")
    xpath_div = xpath_divs[0]
    return xpath_div


def pdf_tries(times=1, sleep=1):
    """
    PDF в ПЭК появляются с задержкой в их методе получшения
    не сразу после регистрации, поэтому и ошибки идут
    добавляю ретрай и задержку на получаемые PDF
    """

    def func_wrapper(f):
        async def wrapper(*args, **kwargs):
            for _ in range(times):
                try:
                    return await f(*args, **kwargs)
                except Exception as exc:
                    logger.info(str(exc))
                    e = exc

                await asyncio.sleep(sleep)
            raise e

        return wrapper

    return func_wrapper
