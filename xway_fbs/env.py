import yaml
from pydantic import BaseSettings

from ozon.consts import CONFIG_DIR

SERVICE_NAME = "xway_fbs"


class Settings(BaseSettings):
    CONECT_MONGO: str | None
    SENTRY_DSN: str | None
    SERVICE_NAME: str = SERVICE_NAME
    LOGIN_AB: str | None
    PASSWORD_AB: str | None
    EPOOL_URL: str = "http://www.epooltest.int/admin/json_zakaz.php"
    XWAY_TOKEN: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    BUCKET: str = "xwaydebugbucket"
    WEIGHT_CALC_URL: str = "http://192.168.0.78:8256"
    XWAY_URL: str = "http://192.168.0.78:8899/api/v1"
    MYSQL: dict = {
        "host": "192.168.0.79",
        "user": "root",
        "password": "",
        "db": "mircomf4_epool",
    }
    MAIL_CRED: dict
    AUTH_TOKEN: str
    OZON_AUTH: dict
    YANDEX_QUEUE_AUTH: dict
    RESERVATION_URL: str
    RESERVATION_TOKEN: str
    YANDEX_QUEUE: dict
    OZON_URL: dict

    class Config:
        env_file = ".env"


SETTINGS = Settings()
with open(CONFIG_DIR) as f:
    config = yaml.safe_load(f)

PLACEMARKET = config["site"]["PLACEMARKET"]
METHOD = config["site"]["CREATE_METHOD"]
ENDPOINT_S3 = config["s3"]["ENDPOINT"]

WEIGHT_CALC_URL = SETTINGS.WEIGHT_CALC_URL + "/weight_calc/sizes/"
BUCKET_NAME_S3 = SETTINGS.BUCKET
XWAY_URL = SETTINGS.XWAY_URL

QUEUE_CREATE = SETTINGS.YANDEX_QUEUE["create"]
QUEUE_TRACE = SETTINGS.YANDEX_QUEUE["trace"]
