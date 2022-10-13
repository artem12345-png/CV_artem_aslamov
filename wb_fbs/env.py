from pydantic import BaseSettings

SERVICE_NAME = "wb_fbs"


class Settings(BaseSettings):
    SERVICE_NAME: str = SERVICE_NAME
    CONECT_MONGO: str | None
    SENTRY_TOKEN: str | None
    LOGIN_AB: str | None
    PASSWORD_AB: str | None
    EPOOL_URL: str = "http://www.epooltest.int/admin/json_zakaz.php"
    XWAY_TOKEN: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    BUCKET: str = "xwaydebugbucket"
    WEIGHT_CALC_URL: str = "http://192.168.0.78:8256"
    XWAY_URL: str = "http://192.168.0.78:8899"
    AUTH_TO_SERVICE: dict = {}
    AUTH_TOKEN_XWAY: str = ""

    YANDEX_QUEUE_AUTH: dict = None
    YANDEX_QUEUES: dict = {"trace": "trace_labels_wb_test"}
    RESERVATION_URL: str = None
    RESERVATION_TOKEN: str = None
    ENDPOINT_S3: str = None

    class Config:
        env_file = ".env"


SETTINGS = Settings()

METHOD = "create_from_market"

WEIGHT_CALC_URL = SETTINGS.WEIGHT_CALC_URL + "/weight_calc/sizes/"
BUCKET_NAME_S3 = SETTINGS.BUCKET
XWAY_URL = SETTINGS.XWAY_URL
PLACEMARKET = "wildberries"
