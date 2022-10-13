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

    CH_HOST: str = None
    CH_USER: str = None
    CH_PASSWORD: str = None
    CH_DATABASE: str = None

    DEBUG: bool = False

    class Config:
        env_file = str(ENV_FILE)


SETTINGS = Settings()
