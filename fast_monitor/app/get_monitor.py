#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Отрисовывает статусы состояния сервисов в ввиде кружков.
"""

from datetime import datetime
import asyncio
import httpx
from PIL import Image, ImageDraw, ImageFont
from app.tools import conection, logger
from io import BytesIO
from app.env_conf import Settings, SETTINGS
from app.consts import FONTS_DIR


async def get_monitors(conf: Settings) -> list:
    url = 'https://api.uptimerobot.com/v2/getMonitors'
    headers = {'Content-Type': 'application/x-www-form-urlencoded',
               'cache-control': 'no-cache'}
    # TODO: Добавил асинхронный httpx
    async with httpx.AsyncClient() as Client:
        offsets = [0, 50]
        monitors_data = []
        for ofs in offsets:
            payload = {'api_key': conf.UPTIME_API_KEY,
                       'format': 'json',
                       'offset': ofs,
                       'logs': 1}

            r = await Client.post(url, data=payload, headers=headers)
            if r.status_code == 200:
                monitors_data += r.json()['monitors']
        # TODO: тут надо работать с асинхронным вариантом httpx
        #  https://www.python-httpx.org/async/
        #  через with

    for e in monitors_data:
        e['logs'] = sorted(e['logs'], key=lambda k: k['datetime'])[-1]
    # asyncio.wait(monitors_data)
    return monitors_data


async def get_flow_statuses(conf: Settings) -> list:
    """ Получает статусы потоков из prefect.io """
    statuses = conection(conf.API_PREFECT_TOKEN)

    return await statuses


def get_image_status(monitors_data: list):
    """ Отрисовывает изображение статусов сервисов.  """
    error = False
    image = Image.new('RGB', (1366, 768), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(
        str(FONTS_DIR / 'DejaVuSansMono.ttf'), 21)
    font_bold = ImageFont.truetype(
        str(FONTS_DIR / 'DejaVuSans-Bold.ttf'), 21)

    max_len_name = len(
        max([e['friendly_name'] for e in monitors_data], key=len))
    # max_len_duration = len(
    #     get_duration(max([e['logs']['duration'] for e in monitors_data])))
    gen_date = datetime.now()
    draw.text((560, 2), gen_date.strftime('%Y-%m-%d %H:%M'),
              (0, 0, 0), font=font_bold)
    draw.line((560, 27, 776, 27), fill=(0, 0, 0))

    n = 4  # разбиение на N столбцов
    monitors_data = list_splitter(monitors_data, n)

    x1, y1 = 24, 32
    x2, y2 = 52, 59
    x_text, y_text = 68, 32

    for data in monitors_data:

        shift = 0
        for e in data:
            name = e['friendly_name']
            name = (name if len(name) == max_len_name
                    else name.ljust(max_len_name))
            # reason = e['logs']['reason']

            status_type = e['status']
            message = (
                f'{name} '
                # f'{date} '
                # f'{duration} '
                # f'{reason["code"]}'
                # f'({reason["detail"]})'
            )
            color_alert = None
            if status_type in [0, 1, 2, 'Success']:
                continue
            elif status_type in [8, 9, 'Failed']:
                color_alert = (206, 11, 15)
                error = True

            draw.ellipse(
                (x1, y1 + shift, x2, y2 + shift), fill=color_alert)
            draw.text((x_text, y_text + shift), message, (0, 0, 0), font=font)
            shift += 29.3
        x1 += 339
        x2 += 339
        x_text += 339

    if error:
        return image


def get_duration(seconds: int):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return '%d:%02d:%02d' % (h, m, s)


def list_splitter(list_, n: int) -> list:
    result = [[] for _ in range(n)]
    cnt = 0
    for e in list_:
        result[cnt].append(e)
        cnt += 1
        cnt = 0 if cnt == n else cnt
    return result


async def build_monitor():
    """ Отрисовывает изображение статусов сервисов.  """

    task1 = asyncio.create_task(get_monitors(SETTINGS))
    task2 = asyncio.create_task(get_flow_statuses(SETTINGS))
    await asyncio.gather(task1, task2)

    logger.info("getting monitors statuses...")
    monitors_data = task1.result()

    logger.info("getting flows statuses...")
    flow_statuses = task2.result()

    logger.info("generating image...")
    monitors_data = monitors_data + flow_statuses
    img = get_image_status(monitors_data)

    if img:
        image = BytesIO()
        img.save(image, format='PNG', quality=85)  # Save image to BytesIO
        del img
        return image.getvalue()
    else:
        img = Image.open('parysnik.jpg')
        image = BytesIO()
        draw = ImageDraw.Draw(img)
        gen_date = datetime.now()
        font_bold = ImageFont.truetype(
            str(FONTS_DIR / 'DejaVuSans-Bold.ttf'), 46)
        draw.text((100, 150), gen_date.strftime('%Y-%m-%d %H:%M'),
                  (0, 0, 0), font=font_bold)
        img.save(image, format='PNG', quality=85)  # Save image to BytesIO
        del img
        return image.getvalue()

