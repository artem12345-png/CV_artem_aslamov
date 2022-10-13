#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from datetime import datetime
from typing import List
import re
import httpx
from aiomysql import DictCursor

from app.configs.app_conf import app_cfg
from app.configs.env_conf import conf
from app.configs.definitions import mm, gr
from app.exceptions import ServiceException
from app.functions.api_lpost import get_auth_token, LPostRequest
from app.models.order import ProductDefault
from app.models.request import RequestData, Data
from app.models.order import OrderList, Order, Cargo, Product, OrderData
from app.tools import (
    MySQLPoolInit, MongoDBInit, check_answer_from_api, get_project_root)
import json

log = logging.getLogger(__name__)


async def create_tasks_to_process_orders(orders, tk_sets, test):
    """Создает задачи на обработку заказов."""

    async with httpx.AsyncClient(timeout=app_cfg.timeout) as ac:
        token = await get_auth_token()

        async with MySQLPoolInit(conf.connection_mysql) as pool:
            async with MongoDBInit(conf.connection_mongo) as client:
                tasks = set()
                len_orders = len(orders)
                for o in orders:
                    db_t = client[app_cfg.db_terminals]
                    db_r = client[app_cfg.db_requests]
                    task = asyncio.create_task(
                        process_order(
                            ac, pool, db_r, db_t, o, token, tk_sets, test)
                    )
                    tasks.add(task)

                done, pending = await asyncio.wait(
                    tasks, timeout=15 * len_orders)

                for task in pending:
                    task.cancel()


async def process_order(
        ac, pool, db_r, db_t, o, token, tk_sets, test):
    """Обрабатывает заказ и создает заявку на доставку."""

    idmonopolia = o.id
    r = RequestData(id=idmonopolia)
    rq = await db_r.requests.find_one({'_id': idmonopolia})
    if not rq or not rq.get('data') or rq.get('error'):
        if rq and rq.get('_id'):
            await db_r.requests.delete_one({'_id': idmonopolia})
            log.info('Удален старый результат для: %s', idmonopolia)

        try:
            order_data = await get_order_data(idmonopolia, pool)
            r.data = await send_request_to_lpost(
                order_data, token, tk_sets, test, ac, db_r, db_t
            )

        except Exception as err:
            log.exception(err)
            r.error = str(err)
            if test:
                raise err

        finally:
            await save_result_to_history_collection(r, db_r)

    else:
        log.info('Информация по заказу idmonopolia: %s найдена в базе.',
                 idmonopolia)


async def get_order_data(idmonopolia, pool) -> OrderData:
    """
    Получаем информацию о заказе по idmonopolia из MySQL
    """
    async with pool.acquire() as conn:
        try:
            async with conn.cursor(DictCursor) as cursor:
                q = """
                SELECT
                    mon4tk.idmonopolia,
                    parts.amount,
                    parts.price,
                    pgs.idgood,
                    pgs.weight,
                    pgs.volume,
                    pgs.`length`,
                    pgs.width,
                    pgs.height,
                    mon4tk.tk,
                    mon4tk.sender_name,
                    mon4tk.idwhs,
                    mon4tk.payer_name,
                    mon4tk.comment_as_site,
                    mon4tk.address,
                    mon4tk.receiver,
                    mon4tk.passport,
                    mon4tk.inn,
                    mon4tk.phone,
                    mon4tk.email
                FROM
                    ep_zakaz_mon4tk AS mon4tk
                INNER JOIN
                    ep_zakaz_monopolia AS parts ON 
                    mon4tk.idmonopolia = parts.idmonopolia
                LEFT JOIN 
                    pr_good_sizes AS pgs ON 
                    parts.idgood = pgs.idgood
                WHERE mon4tk.idmonopolia = %s
                """

                # log.debug(q)
                await cursor.execute(q, [idmonopolia])

                r = await cursor.fetchall()
                if not r:
                    log.info(
                        'В таблице ep_zakaz_monopolia не был найден заказ %s',
                        idmonopolia)

                log.info(
                    'В составе заказа id %s, найдено уникальных товаров %s',
                    idmonopolia, len(r))

                if order_data := get_order_data_with_goods_sizes(r):
                    od = OrderData(**order_data)

                    log.debug(f'order_data: {od.dict()}')

                    return od

                msg = f'Не найдено товаров в заказе: {idmonopolia}'
                log.error(msg)
                raise ServiceException(msg)
        finally:
            await conn.ensure_closed()


def get_order_data_with_goods_sizes(order: List[dict]) -> dict:
    """Собираем данные заказа с товарами."""

    pr_def = ProductDefault()  # Получение значений по умолчанию для товара.
    order_data, goods = dict(), list()
    for e in order:

        weight = float(e.pop('weight'))
        volume = float(e.pop('volume'))
        length = float(e.pop('length'))
        width = float(e.pop('width'))
        height = float(e.pop('height'))
        amount = e.pop('amount')

        # Рассчитываем объем, если получено пустое значение.
        # if not volume and length and width and height:
        #     volume = length * width * height

        good = dict(
            weight=(weight if weight else pr_def.totalWeight) * gr,
            # volume=float(volume) if volume else pr_def.totalVolume,
            length=(length if length else pr_def.length) * mm,
            width=(width if width else pr_def.width) * mm,
            height=(height if height else pr_def.height) * mm,
            idgood=e.pop('idgood'),
            price=float(e.pop('price')),
            amount=amount
        )

        # goods += [good] * amount
        goods.append(good)

        order_data = e

    log.info('Всего уникальных товаров в заказе: %s', len(goods))

    if goods:
        order_data.update({'goods': goods})

    log.debug(f'order_data: {order_data}')

    return order_data


async def send_request_to_lpost(
        order_data: OrderData, token, tk_sets, test, ac, db_r, db_t):
    """Отправляет заполненную заявку, получает накладную в pdf."""

    order = await create_order(
    order_data, token, tk_sets, test, ac, db_t)
    result = await send_order(order, order_data.idmonopolia, token, db_r)

    return result


async def create_order(
        od: OrderData, token, tk_sets, test, ac, db_t) -> dict:
    """Заполняет заявку на доставку груза."""

    dadata_info = await get_info_from_dadata(od.address, ac)
    has_full_address(dadata_info)

    numbers = get_phones_from_txt(od.phone)
    cargoes = get_cargoes(od)

    sum_pre_payment = sum([(e.price * e.amount) for e in od.goods])

    order = Order(
        PartnerNumber=od.idmonopolia,
        # Address=(f'г. {dadata_info["city"]}, '
        #          f'ул. {dadata_info["street"]}, '
        #          f'д. {dadata_info["house"]}'),
        Value=sum_pre_payment,
        SumPrePayment=sum_pre_payment,
        CustomerNumber=od.idmonopolia,
        CustomerName=od.receiver,
        Phone=numbers[0],
        Cargoes=cargoes
    )

    # Добавляем номер терминала.
    if pp_id := await get_pickup_point_id(od, db_t):
        order.ID_PickupPoint = pp_id

    # Добавляем номер квартиры, если указан.
    # if dadata_info.get('flat'):
    #     order.Flat = dadata_info['flat']

    email = get_email_from_txt(od.email) if od.email else 0

    # Проверяем, является ли получатель юр. лицом.
    is_pperson = True if od.payer_name == 'Частное лицо' else False
    if not is_pperson:
        order.isEntity = 1
        order.Email = email

    order_list = OrderList(
        Order=[order]
    )

    # оставляем заполненные поля и дефолтные
    order_list = order_list.dict(exclude_none=True)

    # Запись сформированной заявки для отладки в файл
    if app_cfg.debug:
        with open(f'{get_project_root()}/paylaod.json', 'w',
                  encoding='utf8') as fp:
            json.dump(order_list, fp, ensure_ascii=False)

    return order_list


def get_cargoes(od: OrderData) -> List[Cargo]:
    """Формирует данные о параметрах ящика отправления и его содержимом."""

    # Добавляем данные о товарах в отправлении.
    products = list()
    for g in od.goods:
        product = Product(
            Price=g.price,
            Quantity=g.amount
        )
        products.append(product)

    shipment_sizes = get_shipment_sizes([g.dict() for g in od.goods])[0]
    log.debug(f'shipment_sizes: {shipment_sizes}')

    # Параметры ящика отправления.
    cargo = Cargo(
        Product=products,
        Width=shipment_sizes['width'],
        Height=shipment_sizes['height'],
        Length=shipment_sizes['length'],
        Weight=sum([(e.weight * e.amount) for e in od.goods]),

    )

    return [cargo]


def get_shipment_sizes(goods: List[dict]):
    """Рекурсивно считает примерные размеры груза с товарами."""

    # Выходим, если передан список из одного товара.
    if len(goods) == 1:
        return goods

    full_stack, stack = list(), list()
    for i, g in enumerate(goods, 1):
        stack.append(g)

        # Отбираем по 3 товара.
        if i % 3 == 0:
            full_stack.append(calc_stack_sizes(stack))
            del stack[:]

    if len(stack):
        full_stack.append(calc_stack_sizes(stack))

    return get_shipment_sizes(full_stack)


def calc_stack_sizes(stack):
    """Считает размеры стопки товаров."""

    # Считаем максимальные размеры.
    length = (max([e['length'] for e in stack]), 'length')
    height = (max([e['height'] for e in stack]), 'height')
    width = (max([e['width'] for e in stack]), 'width')

    # Находим минимальное измерение.
    min_param = min([length, height, width], key=lambda x: x[0])

    key = min_param[1]
    # Суммируем наименьшее размерение.
    sum_param = (sum(e[key] for e in stack), key)

    if key == 'length':
        length = sum_param
    elif key == 'width':
        width = sum_param
    elif key == 'height':
        height = sum_param

    r = dict(
        length=length[0],
        height=height[0],
        width=width[0]
    )

    return r


async def get_info_from_dadata(address, ac_dd) -> dict:
    """Получает информацию об адресе через API сервиса dadata.ru"""

    if not address:
        raise ServiceException('Передано пустое поле адрес.')

    headers = {
        'Authorization': f'Token {conf.dadata_token}',
        'X-Secret': conf.dadata_xsecret
    }

    payload = [address]

    r = await ac_dd.post(app_cfg.dadata_url, headers=headers, json=payload)
    r = check_answer_from_api(r, 'Ошибка получения данных c dadata.ru')

    result = r.json()[0]
    log.debug('Получены данные по адресу c dadata.ru: %s', result)

    return result


def has_full_address(dadata_info):
    """Проверяет, является ли адрес полным: город, улица, дом, квартира."""

    # Если в dadata передать 'Москва', то 'city' = None, 'region' = 'Москва'
    city = dadata_info['city'] or dadata_info['region']
    street = dadata_info['street']
    house = dadata_info['house']
    # flat = dadata_info['flat']

    # Если у нас нет или улицы или дома, то у нас нет полного адреса.
    if city and (not street or not house):
        return False
    elif city and street and house:
        return True

    msg = f'Не удалось распознать адрес: {dadata_info["source"]}'
    log.error(msg)
    raise ServiceException(msg)


def get_phones_from_txt(phones_txt) -> list:
    """Выпарсивает мобильные телефоны со строки."""

    log.debug(f'phones: {phones_txt}')

    if not phones_txt:
        msg = 'Обнаружено пустое поле: phone.'
        log.error(msg)
        raise ServiceException(msg)

    result = list()

    if phones := re.findall(
            r'(\+7|8)[- _]*\(?[- _]*(\d{3}[- _]*\)?([- _]*\d){7}|\d'
            r'\d[- _]*\d\d[- _]*\)?([- _]*\d){6})',
            phones_txt,
    ):

        for p in phones:
            part_phone = p[1]

            for e in [' ', '(', ')', '-']:  # Очистка от символов
                part_phone = part_phone.replace(e, '')

            result.append(part_phone)

        return result

    msg = f'Не удалось получить моб. телефоны со строки: {phones_txt}'
    log.error(msg)
    raise ServiceException(msg)


async def get_pickup_point_id(od: OrderData, db_t) -> int:
    """Получает id терминала, если передан."""

    tk_field = od.tk.lower()
    if 'терминал' in tk_field:
        terminal_id = await get_terminal_id_from_field(tk_field, db_t)

        return terminal_id


async def get_terminal_id_from_field(tk_field, db_t) -> int:
    """Получает id терминала из поля tk."""

    if r := re.search(r'\[\s*\+?(-?\d+)\s*]', tk_field):
        terminal_id = r.group(1)

        # Проверяем, существует ли такой терминал.
        if await db_t.lpost_terminals.find_one({'_id': int(terminal_id)}):
            log.info('В поле tk, найден id терминала: %s', terminal_id)

            return terminal_id

        msg = f'Получен несуществующий id терминала: {terminal_id}'
        log.error(msg)
        raise ServiceException(msg)


def get_email_from_txt(email_txt):
    """Получение и очистка email из текстового поля."""

    for s in [';', ':']:
        email_txt = email_txt.replace(s, ',')

    emails = email_txt.split(',')
    emails = [e for e in emails if e]

    if emails:
        return emails[0]  # Берем первый email из списка


async def send_order(order, idmonopolia, token_lpost, db):
    """Отправка сформированной заявки в dellin.ru"""

    log.debug(f'order: {order}')

    payload = dict(
        method='CreateOrders',
        token=token_lpost['token'],
        ver=1,
        json=json.dumps(order)
    )

    init = dict(
        url=app_cfg.api_url,
        err_msg='Ошибка получения данных c Л-Пост.',
        db=db,
        payload=payload,
    )

    async with LPostRequest(**init) as lpr:
        r = await lpr.post()
        result = r.json()

        log.debug(f'result: {result}')


async def save_result_to_history_collection(result: RequestData, db):
    result = result.dict()

    body = dict(dt=datetime.now(), data=result['data'])

    if error := result.get('error'):
        body.update({'error': error})

    body.update({'_id': result['id']})

    await db.requests.replace_one({'_id': result['id']}, body, True)

    log.info(
        'В коллекцию %s, записаны данные для заказа id: %s', db.requests.name,
        result['id'])
