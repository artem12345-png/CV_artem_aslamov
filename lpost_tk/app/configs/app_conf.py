#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List

from httpx import Timeout
from pydantic import BaseModel


class AppSettings(BaseModel):
    debug: bool = True  # Делает тестовые заказы, как реальные.

    maintainer: str = 'Artem Aslamov'

    tk_id: int = 10  # Код транспортной компании.

    api_url = 'https://apitest.l-post.ru/'

    dadata_url: str = 'https://cleaner.dadata.ru/api/v1/clean/address'

    s3_bucket: str = 'lpost'
    s3_dir_labels: str = 'labels' if not debug else 'debug-labels'
    s3_dir_total_labels: str = (
        'total-labels' if not debug else 'debug-total-labels')
    s3_dir_total_acts: str = 'acts' if not debug else 'debug-total-acts'

    timeout: Timeout = Timeout(15.0, connect=10.0)

    db_requests: str = 'lpost_tk'  # Коллекция хранения заявок.
    db_terminals: str = 'delivery_lists'
    db_settings: str = 'epool_admin'

    static_dir: str = 'static'
    font_name: str = 'FreeSans_bold.ttf'

    tz: str = 'Europe/Moscow'

    sentry_sample_rate: float = 0.25

    local_host: str = '0.0.0.0'
    port: int = 7585

    class Config:
        arbitrary_types_allowed = True


class AllowedCities(BaseModel):
    """Разрешенные города отправки со складов."""

    cities: List = list()  # Список для id складов в городах.


class Payer(BaseModel):
    """Настройки кто является плательщиком."""

    package: str = 'receiver'  # Плательщик за упаковку/обрешетку.
    derival: str = 'receiver'  # Плательщик за забор со склада.
    arrival: str = 'receiver'  # Плательщик за доставку.


class TKSettings(BaseModel):
    payer: Payer = Payer()
    allowed_cities: AllowedCities = AllowedCities()


app_cfg = AppSettings()
