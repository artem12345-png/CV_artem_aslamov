#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pydantic import BaseSettings, Field
from app.consts import ENV_FILE


class Settings(BaseSettings):
    # переменная позволяющая понять на каком сервере запускается наша программа
    # при этом локально можно не указывать
    DOCKER_HOST: str = Field(default=None)

    SERVICE_NAME: str = None
    FLUENTD_HOST: str = None
    SENTRY_DSN: str = None
    URL: str = None
    CONNECTION: str = None

    DEBUG: bool = False

    class Config:
        env_file = str(ENV_FILE)


SETTINGS = Settings()
