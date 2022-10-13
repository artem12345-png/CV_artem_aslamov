#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pydantic import BaseSettings, Field
from app.consts import ENV_FILE


class Settings(BaseSettings):
    UPTIME_API_KEY: str = None
    API_PREFECT_TOKEN: str = None
    # переменная позволяющая понять на каком сервере запускается наша программа
    # при этом локально можно не указывать
    DOCKER_HOST: str = Field(default=None)

    SERVICE_NAME: str = None
    #
    #
    FLUENTD_HOST: str = None
    SENTRY_DSN: str = None

    SQL_HOST: str = None
    SQL_USER: str = None
    SQL_PASSWORD: str = None
    SQL_DATABASE: str = None

    DEBUG: bool = False

    class Config:
        env_file = ".env"


SETTINGS = Settings()
