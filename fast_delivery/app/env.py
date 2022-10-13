from pydantic import BaseSettings

SERVICE_NAME = "fast_delivery"


class Settings(BaseSettings):
    CDEK_OFF: bool = False
    PECOM_OFF: bool = False
    SKIFF_OFF: bool = False
    BAIKAL_OFF: bool = False
    PICKPOINT_OFF: bool = False
    JDE_OFF: bool = False
    STATUS_OFF: bool = False
    DEBUG: bool = False
    ##########
    DADATA: dict
    DELIVERY_CALC_URL_PROD: str
    DELIVERY_CALC_URL_TEST: str = "http://192.168.0.78:7337/delivery_calc"
    JDE_AUTH: dict
    PECOM_AUTH: dict
    CDEK_AUTH: dict
    SK_AUTH: dict
    BL_AUTH: dict
    S3_AUTH: dict
    PICKPOINT_AUTH: dict
    PICKPOINT_IKN_PROD: str = "9990908312"
    PICKPOINT_IKN_TEST: str = "9990000112"
    ##########
    MYSQL: dict
    MYSQL_WRITE: dict
    MONGODB_CONNECTION_STRING: str
    ##########
    GITLAB_PRIVATE_TOKEN: str = None
    DOCKER_HOST: str = None
    SERVICE_NAME: str = SERVICE_NAME

    class Config:
        env_file = ".env"


SETTINGS = Settings()
