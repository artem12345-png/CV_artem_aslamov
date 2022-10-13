from urllib.parse import unquote_plus

import yaml

from app.db.wrappers import MySQL, MongoDB
from app.env import SETTINGS
from app.routes.pickpoint.consts import PICKPOINT_TEST_BASE_URL, PICKPOINT_BASE_URL
from app.settings.consts import (
    CONFIG_DIR,
)
from app.settings.log import logger

CONFIG = dict()


def load_config(is_update_statuses=True, test=False):
    logger.info("Загружаем CONFIG")
    CONFIG["test"] = test or SETTINGS.DEBUG
    CONFIG["is_update_statuses"] = is_update_statuses

    with open(CONFIG_DIR / "app.yaml") as f:
        CONFIG["app"] = yaml.safe_load(f)

    CONFIG["dadata"] = _load_dadata_config()

    CONFIG["mysql"] = MySQL.read_settings_async()
    CONFIG["mysql_write"] = MySQL.read_settings_async(prefix="WRITE")

    CONFIG["mongodb"] = MongoDB.read_settings_async()

    CONFIG["delivery_calc"] = _load_delivery_calc_config()
    logger.info("CONFIG загружен")


def _load_dadata_config():
    c = dict(token=SETTINGS.DADATA["token"], secret=SETTINGS.DADATA["secret"])
    return c


def _load_delivery_calc_config():
    c = dict(
        prod_url=SETTINGS.DELIVERY_CALC_URL_PROD,
        test_url=SETTINGS.DELIVERY_CALC_URL_TEST,
    )
    return c


def load_pecom_config():
    c = dict(
        PECOM_USER=SETTINGS.PECOM_AUTH["user"],
        PECOM_ACCESS_TOKEN=SETTINGS.PECOM_AUTH["access_token"]["prod"],
        PECOM_ACCESS_TOKEN_TEST=SETTINGS.PECOM_AUTH["access_token"]["test"],
        PECOM_PASS=SETTINGS.PECOM_AUTH["pass"],
    )
    return c


def load_cdek_config(config: dict) -> dict[str, dict]:
    cdek_conf = config["app"]["fast_delivery"]["cdek"]
    c = {}
    cdek_auth = SETTINGS.CDEK_AUTH
    for _delivery_name in cdek_conf:
        delivery_name = _delivery_name.upper()
        d_n_l = delivery_name.lower()
        cdek_c = c[f"cdek_{delivery_name.lower()}"] = {}
        cdek_c["name"] = cdek_conf[_delivery_name]["name"]
        cdek_c["credentials"] = dict(
            account=cdek_auth[d_n_l]["account"],
            secret=cdek_auth[d_n_l]["secret"],
        )
    return c


def load_skiff_config() -> dict[str, dict]:
    return {
        "SK_LOGIN_API": SETTINGS.SK_AUTH["api"]["login"],
        "SK_PASS_API": unquote_plus(SETTINGS.SK_AUTH["api"]["pass"]),
        "SK_LOGIN_UI": SETTINGS.SK_AUTH["ui"]["login"],
        "SK_PASS_UI": SETTINGS.SK_AUTH["ui"]["pass"],
    }


def load_baikal_config() -> dict[str, str]:
    return {
        "BL_LOGIN_UI": SETTINGS.BL_AUTH["ui"]["prod"]["login"],
        "BL_PASS_UI": SETTINGS.BL_AUTH["ui"]["prod"]["pass"],
        "BL_LOGIN_UI_TEST": SETTINGS.BL_AUTH["ui"]["test"]["login"],
        "BL_PASS_UI_TEST": SETTINGS.BL_AUTH["ui"]["test"]["pass"],
    }


def load_pickpont_config() -> dict[str, dict]:
    pp_conf_test = {
        "credentials": dict(
            login=SETTINGS.PICKPOINT_AUTH["test"]["login"],
            password=SETTINGS.PICKPOINT_AUTH["test"]["pass"],
            base_url=PICKPOINT_TEST_BASE_URL,
            test=True,
        )
    }
    pp_conf_prod = {
        "credentials": dict(
            login=SETTINGS.PICKPOINT_AUTH["prod"]["login"],
            password=SETTINGS.PICKPOINT_AUTH["prod"]["pass"],
            base_url=PICKPOINT_BASE_URL,
        )
    }
    pp_conf = {"prod": pp_conf_prod, "test": pp_conf_test}
    return pp_conf
