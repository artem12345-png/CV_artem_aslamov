#!/usr/bin/env python3

from datetime import date, datetime
from pathlib import Path
from io import BytesIO
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from app.db import DBS
from app.env_conf import Settings
from app.tools import logger
from aiochclient import ChClient as Client

matplotlib.use('Agg')

Y_MAX = 3
MIN_IMG_CNT = 709000

servers = ['daemon2', '3', 'daemon3', 'daemon4']  # , 'video', 'logstash']


class Formatter(mdates.DateFormatter):
    def __call__(self, x, pos=None):
        return super().__call__(x).replace(':00', '')


async def build_chart():
    logger.info("Draw script started")
    Y_MAX = 3

    # Init connection
    # TODO: мы уже загрузили Settings
    # conf = Settings()

    # Нам не нужно каждый раз подключаться к кликхаусу
    # conf_clickhouse = get_clickhouse_conf(conf)

    clickhouse: Client = DBS['clickhouse']['client']

    # Get data
    logger.info("Get data...")

    query = (
        "SELECT "
        "   _time AS ts, "
        "   response_time / 1000000 AS timer "
        "FROM apache "
        "WHERE "
        f"  (_date = '{date.today()}') AND "
        "   (request_type = 'GET') AND "
        "   (response_code = 200) AND "
        f"  (request_url LIKE '/good/%') "
        "ORDER BY ts ASC"
    )

    db_data = [list(r.values()) for r in await clickhouse.fetch(query)]

    columns = ['time', 'response']
    df = pd.DataFrame(db_data, columns=columns)
    # cursor.close()
    logger.info("Data received")

    if len(df.index) == 0:
        logger.info("Data is empty.")
        return

    # TODO: вопросик
    # self_check(df['time'].tail(1))

    # Configure plot
    fig = plt.figure(figsize=(18, 6))
    ax = fig.add_subplot(1, 1, 1)
    ax.grid()
    ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=[5, 10, 15, 20, 25, 35, 40, 45, 50, 55]))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))  # to get a tick every 30 minutes
    #    ax.xaxis.set_major_formatter(mdates.DateFormatter('%-H:%-M'))     #optional formatting
    ax.xaxis.set_major_formatter(Formatter('%-H:%M'))  # optional formatting
    #############################################################################
    # TODO: почему работа сначала с fig ax, а потом с plt
    plt.ylim([0, Y_MAX * 1.01])
    plt.title(pd.to_datetime(str(df.time.values[-1])).strftime('%Y-%m-%d %-H:%M'))

    # Draw on plot
    x = df.time
    y = df.response

    idx = (y < Y_MAX * 0.99)
    plt.plot(x[idx], y[idx], marker='.', linestyle='None', color='blue', alpha=0.1)
    plt.plot(x[~idx], y[~idx], marker='*', linestyle='None', color='red')
    ############################################################################

    # # Draw servers
    # for i, server in enumerate(servers):
    #     if not is_slave_healthy(server):
    #         lbl = '*' + ''.join(set(server[:1].upper() + server[-1:].upper()))
    #         ax.annotate(lbl,
    #                     xy=(275 + i * 400, 380),
    #                     xycoords='figure pixels',
    #                     fontsize=128,
    #                     color='red')

    # # Draw annotate
    # cnt = get_img_count()
    # if cnt < MIN_IMG_CNT:
    #     ax.annotate('images: {}%'.format(int(cnt / MIN_IMG_CNT * 100)), xy=(300, 100),
    #                 xycoords='figure pixels',
    #                 fontsize=64,
    #                 color='red')

    chart = BytesIO()
    plt.savefig(fname=chart, format='PNG')

    plt.close(fig)
    plt.clf()
    plt.cla()

    return chart.getvalue()


def self_check(time_np):
    """
    Функция пишет в файл статус о заливке логов в БД

    Если время заливки последнего лога более чем 10 минут,
    то мы считаем, что произошла ошибка

    Если нет, то все норм.

    TODO: !!! РАБОТА ФУНКЦИИ В СЕРВИСЕ ДОЛЖНА БЫТЬ ОБСУЖДЕНА С ДК !!!

    :param: time_np [np.datetime] - время последнего лога в БД
    """
    with open('clickhouse.txt', 'w') as f:
        time_diff = np.datetime64(datetime.now()) - time_np
        if int(time_diff / np.timedelta64(1, 'm')) > 10:
            f.write('ERROR')
        else:
            f.write('OK')


# def get_clickhouse_conf(conf) -> dict:
#    config = dict(
#        host=conf.CH_HOST,
#        user=conf.CH_USER,
#        password=conf.CH_PASSWORD,
#        database=conf.CH_DATABASE
#    )
#    return config


def get_img_count():
    try:
        with open('image_count.txt') as f:
            s = f.readlines()
            cnt = int(s[1])
    except:
        cnt = 0
    return cnt


def is_slave_healthy(server_name):
    try:
        fn = server_name + '.txt'
        cols_yes = ['Slave_IO_Running', 'Slave_SQL_Running']
        cols_zero = ['Last_Errno', 'Last_SQL_Errno', 'Last_IO_Errno']
        cols_empty = ['Last_Error', 'Last_IO_Error', 'Last_SQL_Error']

        with open(fn, 'r') as f_in:
            lines = dict([y.strip() for y in x.split(':', 2)] for x in [x.strip() for x in f_in][1:])

        return (all(lines[x] == 'Yes' for x in cols_yes)
                and all(lines[x] == '0' for x in cols_zero)
                and all(lines[x] == '0' for x in cols_zero)
                and (float(lines['Seconds_Behind_Master']) < 300))
    except Exception as e:
        # print("Unexpected error:", fn, sys.exc_info())
        return False
