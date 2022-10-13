#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging

from fastapi import Depends, status as sc
from fastapi import FastAPI, BackgroundTasks

from app.functions.api_lpost import LPostRequest, get_auth_token
from .configs.app_conf import app_cfg, TKSettings
from .configs.env_conf import conf
from .functions.create_orders import create_tasks_to_process_orders
from .functions.general import (
    check_auth_token,
    save_orders_and_get_task_token,
    get_settings_from_mongodb,
    check_database_connections,
    response_simple_decorator,
    mongo_decorator)
from .models.models import TaskToken
from .models.request import OrdersRequest, DeleteOrderRequest, CreateActRequest
from .tools import MongoDBInit

app = FastAPI(debug=app_cfg.debug)

log = logging.getLogger(__name__)


@app.post('/create_orders',
          dependencies=[Depends(check_auth_token)], response_model=TaskToken)
async def send_request(
        req_data: OrdersRequest, background_tasks: BackgroundTasks):
    """Принимает заказы на создание отравлений на доставку."""

    log.info('Запрос /create_orders с составом: %s', req_data.dict())

    orders = req_data.arr
    test = req_data.test
    tk_sets = TKSettings()

    async with MongoDBInit(conf.connection_mongo) as client:
        db_r = client[app_cfg.db_requests]
        package_token = await save_orders_and_get_task_token(orders, db_r)
        db_s = client[app_cfg.db_settings]
        tk_sets = await get_settings_from_mongodb(tk_sets, db_s)

    background_tasks.add_task(
        create_tasks_to_process_orders, orders, tk_sets, test)

    return TaskToken(token_id=package_token)


@app.post('/create_act', dependencies=[Depends(check_auth_token)])
@mongo_decorator
async def create_act(req_data: CreateActRequest, db=None):
    """ Создание акта для массива отправлений. """

    log.info('Запрос: /create_act')

    token = await get_auth_token()

    payload = dict(
        method='CreateAct',
        token=token['token'],
        ver=1,
        json=json.dumps(req_data.dict())
    )

    init = dict(
        url=app_cfg.api_url,
        err_msg='Ошибка получения данных c Л-Пост, метод CreateAct.',
        db=db,
        payload=payload,
    )

    async with LPostRequest(**init) as lpr:
        r = await lpr.post()
        result = r.json()

        log.debug(f'result: {result}')


@app.post('/update_orders', dependencies=[Depends(check_auth_token)])
async def update_orders(req_data: OrdersRequest):
    """ Изменение данных по массиву отправлений до момента создания акта. """

    pass


@app.post('/delete_orders', dependencies=[Depends(check_auth_token)])
@mongo_decorator
async def delete_orders(req_data: DeleteOrderRequest, db=None):
    """ Удаление массива отправлений до момента создания акта. """

    log.info('Запрос: /delete_orders')

    token = await get_auth_token()

    payload = dict(
        method='DeleteOrders',
        token=token['token'],
        ver=1,
        json=json.dumps(req_data.dict())
    )

    init = dict(
        url=app_cfg.api_url,
        err_msg='Ошибка получения данных c Л-Пост, метод DeleteOrders.',
        db=db,
        payload=payload,
    )

    async with LPostRequest(**init) as lpr:
        r = await lpr.delete()
        result = r.json()

        log.debug(f'result: {result}')


@app.post('/get_cargoes_labels', dependencies=[Depends(check_auth_token)])
async def get_cargoes_labels(req_data: OrdersRequest):
    """ Получение этикеток для ящиков."""

    pass


@app.post('/get_acts_labels', dependencies=[Depends(check_auth_token)])
async def get_acts_labels(req_data: OrdersRequest):
    """ Получение печатной формы акта приема-передачи. """

    pass


@app.post('/get_state_orders', dependencies=[Depends(check_auth_token)])
async def get_state_orders(req_data: OrdersRequest):
    """ Получение текущего состояния по массиву отправлений. """

    pass


@app.post('/get_states_orders_history',
          dependencies=[Depends(check_auth_token)])
async def get_states_orders_history(req_data: OrdersRequest):
    """ Получение истории изменения статусов для массива отправлений. """

    pass


@app.post('/token_check/',
          dependencies=[Depends(check_auth_token)])
def check_token():
    return {'token': 'Ok'}


@app.get('/self_check/')
@response_simple_decorator
@mongo_decorator
async def self_check(req_data='', status_code=sc.HTTP_500_INTERNAL_SERVER_ERROR, db=None):
    # log.info('Status %s', 'Ok')
    return {'status': 'Ok'}
