from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    auth_token: str = 'qwerty'
    sentry_dsn: str | None = ''
    service_name: str = 'lpost_tk'
    docker_host: str = ''
    fluentd_host: str = ''
    lpost_api: str

    lpost_secret: str  # Секрет для получения токена.

    connection_mongo: str
    connection_mysql: dict
    # connection_mysql_rw: dict | None = None

    s3_auth: dict

    dadata_token: str
    dadata_xsecret: str

    class Config:
        env_file = f'{Path(__file__).parent.parent.parent}/.env'


conf = Settings()
