#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from functools import wraps

from aiomysql import DictCursor
from fastapi import HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette import status

from app.configs.app_conf import app_cfg, Payer, AllowedCities
from app.configs.env_conf import conf
from app.exceptions import ServiceException
from app.models.models import ResultResponse
from app.tools import (
    MongoDBInit,
    MySQLInit)

log = logging.getLogger(__name__)

auth_token = APIKeyHeader(name='Authorization')


async def check_auth_token(token: str = Depends(auth_token)):
    """Проверят авторизационный токен из заголовка запроса от пользователя."""

    if token != conf.auth_token:
        log.info('Получен невалидный токен: %s', auth_token)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid token.')

    log.info('Получен валидный токен.')


async def check_database_connections(db):
    try:
        await db.requests.aggregate([
            {'$match': {}},
            {'$limit': 1}]).to_list(length=None)

    except Exception as e:
        raise ServiceException('Ошибка соединения с mongodb: %s', str(e))

    try:
        async with MySQLInit(conf.connection_mysql) as conn:
            async with conn.cursor(DictCursor) as cursor:
                q = """
                SELECT
                    idgood,
                    store
                FROM
                    ep_store_whs esw
                LIMIT 1
                """

                await cursor.execute(q)
                await cursor.fetchall()

    except Exception as e:
        raise ServiceException('Ошибка соединения с MySQL: %s', str(e))


async def save_orders_and_get_task_token(orders, db) -> str:
    """Сохраняет пакеты заказов в mongodb и возвращает их токен задачи."""

    r = await db.tasks.insert_one({'orders': [o.dict() for o in orders]})
    return str(r.inserted_id)


async def get_settings_from_mongodb(tk_sets, db):
    """Получает настройки для сервиса из коллекции MongoDB."""

    r = await db.tk_config.find_one({'_id': app_cfg.tk_id})

    payer = Payer()
    ac = AllowedCities()

    if r:
        customer_pays_for_pickup = r['customer_pays_for_pickup']
        customer_pays_for_delivery = r['customer_pays_for_delivery']
        pickup_msk = r['pickup_msk']
        pickup_nsk = r['pickup_nsk']

        if not customer_pays_for_pickup:
            payer.package = 'sender'
            payer.derival = 'sender'

        if not customer_pays_for_delivery:
            payer.arrival = 'sender'

        if pickup_msk:
            ac.cities.append(101)  # id склада в Москве
        if pickup_nsk:
            ac.cities.append(100)  # id склада в Новосибирске

        tk_sets.payer = payer
        tk_sets.allowed_cities = ac

        log.debug('TK settings: %s', tk_sets.dict())

        return tk_sets

    else:
        log.error('Не найдены настройки сервиса в базе.')
        return tk_sets


async def save_log_to_mongodb(
        db, address: str, direction: str, req=None, resp=None):
    """Записывает логи запросов к сервису в MongoDB."""

    data = dict(
        address=address,
        direction=direction,
        date=datetime.now()
    )

    if req:
        data['request'] = (
            req.dict(exclude_none=True) if not isinstance(
                req, dict) else req)

    if resp:
        data['response'] = (
            resp.dict(exclude_none=True) if not isinstance(
                resp, dict) else resp)

    log.debug('Data log: %s', data)

    try:
        await db.api_log.insert_one(data)
        log.debug('Лог с адреса: %s, сохранен в mongodb.', address)

    except ServiceException:
        log.error('Ошибка записи лога в mongodb, с адреса: %s', address)


def mongo_decorator(func):
    @wraps(func)
    async def mongo_inner_function(*args, **kwargs):
        async with MongoDBInit(conf.connection_mongo) as client:
            db = client[app_cfg.db_requests]
            kwargs.update({'db': db})
            resp = await func(*args, **kwargs)

            return resp

    return mongo_inner_function


def response_decorator(func):
    @wraps(func)
    async def response_inner_function(*args, **kwargs):
        resp = ResultResponse(result='OK')
        try:
            resp = await func(*args, **kwargs)

            return resp

        except Exception as err_msg:
            log.error(err_msg)

            resp.result = 'ERROR'
            resp.msg = str(err_msg)

            return JSONResponse(
                status_code=kwargs['status_code'],
                content=resp.dict(exclude_none=True))

    return response_inner_function


def response_simple_decorator(func):
    @wraps(func)
    async def response_simple_inner_function(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)

            return result

        except Exception as err_msg:
            log.error(err_msg)

            raise HTTPException(
                status_code=kwargs['status_code'],
                detail=str(err_msg))

    return response_simple_inner_function
