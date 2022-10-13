from pathlib import Path
from collections import defaultdict

from app.env import SETTINGS

DEBUG = SETTINGS.DEBUG

ROOT_DIR = Path(__name__).parent.parent.absolute()

(ROOT_DIR / "logs").mkdir(exist_ok=True)

COOKIE_DIR = ROOT_DIR / "cookies"
COOKIE_DIR.mkdir(exist_ok=True)

COOKIE_SCREENSHOT_DIR = ROOT_DIR / "cookie_screenshots"
COOKIE_SCREENSHOT_DIR.mkdir(exist_ok=True)

CONFIG_DIR = ROOT_DIR / "config"
CONFIG_DIR.mkdir(exist_ok=True)

PUBLIC_DIR = ROOT_DIR / "public"
PUBLIC_DIR.mkdir(exist_ok=True)

FONT_PATH = CONFIG_DIR / "FreeSans.ttf"
if not FONT_PATH.exists():
    raise Exception(f"font {FONT_PATH.name} must be placed in config_dir: {CONFIG_DIR}")

VERSION = "2021.02.17"

MSG_SERVICE_DESCRIPTION = "It's just simple unnamed project"

NUM_PLACE = 1

COOKIE_EXPIRES_SECONDS = 24 * 60 * 60
COOKIE_WAIT_SECONDS = 120
STATUS_UPDATE_CYCLE = 60 * 30

TK_ID_DICT = {1: "baikal", 3: "pecom", 4: "jde", 5: "skiff", 6: "cdek", 8: "pickpoint"}
TK_ID_NAME = {
    1: "Байкал-Сервис",
    3: "ПЭК",
    4: "ЖелДорЭкспедиция",
    5: "Скиф-Карго",
    6: "СДЭК",
    8: "Pickpoint",
}
TK_ID_COLL_NAME = {
    1: "baykal_terminals",
    3: "pek_terminals",
    4: "jde_terminals",
    6: "cdek_terminals",
    8: "pickpoint_terminals",
}
TK_SMS_STATUSES = {
    1: ["Подтверждена"],  # Байкал-сервис
    3: ["Оформлен"],  # ПЭК
    4: ["посылка находится на терминале приема отправления"],  # ЖелДор
    5: ["груз на складе"],  # СКИФ
    6: ["Принят на склад отправителя"],  # СДЭК
    8: ["Сформирован для передачи Логисту"],
}
SMS_SENDER = "epool"
URL_SEND_TEST = "http://192.168.0.78:7730/sent_mts/"
URL_SEND = "http://7.epool.ru:7730/sent_mts/"


def cities_factory():
    return ["Москва"]


ALLOWED_CITIES = defaultdict(cities_factory)
ALLOWED_CITIES[3] = ["Москва", "Новосибирск"]
ALLOWED_CITIES[6] = ["any"]


TK_TRACK_URL = {
    1: lambda x: "https://www.baikalsr.ru/tools/tracking/",
    3: lambda x: "http://pecom.ru/services-are/order-status/",
    4: lambda x: f"https://i.jde.ru/orders_pin/?ttn={x[0][:4] + '-' + x[0][4:8] + '-' + x[0][8:12] + '-' + x[0][12:16]}&pin={x[1]}",
    6: lambda x: f"https://www.cdek.ru/track.html?order_id={x['tk_num']}",
    5: lambda x: "https://www.skif-cargo.ru/tracking/",
    8: lambda x: "https://pickpoint.ru/monitoring/",
}

TK_ID_QUERY = {
    1: lambda dadata: (
        {"city_uid": dadata.region_fias_id},
        {"title": dadata.city or dadata.region, "address": 1},
    ),
    2: lambda dadata: (
        {"fullAddress": {"$regex": f".*{dadata.city} г.*"}},
        {"fullAddress": 1},
    ),
    3: lambda dadata: (
        {"address": {"$regex": f".*г?{dadata.city or dadata.region}.*"}},
        {"title": "$divisionName", "address": 1},
    ),
    4: lambda dadata: (
        {"city": dadata.city or dadata.region},
        {"title": "city", "address": "$addr"},
    ),
    6: lambda dadata: (
        {"location.city": dadata.city or dadata.region},
        {"title": "$location.city", "address": "$location.address_full"},
    ),
    8: lambda dadata: (
        {"FiadId": dadata.region_fias_id},
        {"title": dadata.city, "address": "$Address"},
    ),
}

assert len(TK_ID_DICT.keys()) == len(TK_SMS_STATUSES.keys()) == len(TK_TRACK_URL.keys())
SENDER_CONTACT = "Назаров Алексей"
TEMPLATE_EMAIL = "support@promsoft.ru"
