#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from app.configs.app_conf import app_cfg
from app.configs.env_conf import conf
from app.exceptions import ServiceException
from app.functions.general import save_log_to_mongodb
from app.tools import (
    check_answer_from_api,
    get_json_response)

log = logging.getLogger(__name__)


class LPostRequest:
    """Объект взаимодействия с API Я.Маркет."""

    def __init__(
            self,
            url: str,
            err_msg: str,
            db: AsyncIOMotorClient,
            payload=None
    ):
        self.db = db
        self.url = url
        self.json = payload
        self.err_msg = err_msg

    async def __aenter__(self):
        self.ac = httpx.AsyncClient(timeout=app_cfg.timeout)
        return self

    async def post(self):
        if self.db is not None:
            await save_log_to_mongodb(self.db, self.url, 'out', req=self.json)

        r = await self.ac.post(self.url, data=self.json)
        r = check_answer_from_api(r, self.err_msg)

        if self.db is not None:
            if resp_json := get_json_response(r):
                await save_log_to_mongodb(
                    self.db, self.url, 'out', resp=resp_json)

        return r

    async def get(self):
        await save_log_to_mongodb(self.db, self.url, 'out')

        r = await self.ac.get(self.url)
        r = check_answer_from_api(r, self.err_msg)

        if resp_json := get_json_response(r):
            await save_log_to_mongodb(self.db, self.url, 'out', resp=resp_json)

        return r

    async def delete(self):
        await save_log_to_mongodb(self.db, self.url, 'out')

        r = await self.ac.request(
            method="DELETE", url=self.url, data=self.json)
        r = check_answer_from_api(r, self.err_msg)

        if resp_json := get_json_response(r):
            await save_log_to_mongodb(self.db, self.url, 'out', resp=resp_json)

        return r

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.ac.aclose()


async def get_auth_token():
    """Получает токен для работы с API Л-Пост."""

    log.info('Получаем временный токен доступа от api Л-Пост.')

    payload = dict(
        method='Auth',
        secret=conf.lpost_secret
    )

    init = dict(
        url=app_cfg.api_url,
        payload=payload,
        err_msg='Ошибка получения данных c Л-Пост.',
        db=None
    )

    async with LPostRequest(**init) as lpr:
        r = await lpr.post()
        result = r.json()

        if 'errorMessage' in result:
            err_msg = (
                f'Ошибка получения токена Л-Поста: {result["errorMessage"]}')
            log.error(err_msg)
            raise ServiceException(err_msg)

        log.info('Токен получен, истекает: %s', result['valid_till'])

        return result
