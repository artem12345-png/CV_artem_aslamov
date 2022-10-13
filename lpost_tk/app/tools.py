#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import logging.config
import os
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import aiomysql
import sentry_sdk
import yaml
from aiobotocore.session import get_session
from motor.motor_asyncio import AsyncIOMotorClient

from .configs.app_conf import app_cfg
from .configs.env_conf import conf
from .exceptions import ServiceException

self_path = Path(__file__)
log = logging.getLogger(__name__)


class MySQLInit:
    def __init__(self, connection_dict: dict):
        self._conn = None
        self._connection_dict = connection_dict

    async def __aenter__(self):
        self._connection_dict.update(dict(autocommit=True))
        self._conn = await aiomysql.connect(**self._connection_dict)
        return self._conn

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._conn.ensure_closed()


class MySQLPoolInit:
    def __init__(self, connection_dict: dict, pool_size: int = None):
        self._pool = None
        self._connection_dict = connection_dict
        self._pool_size = 5 if not pool_size else pool_size  # DK не более 5

    async def __aenter__(self):
        self._connection_dict.update(
            dict(
                minsize=0,
                maxsize=self._pool_size,
                autocommit=True
            ))
        self._pool = await aiomysql.create_pool(**self._connection_dict)
        return self._pool

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._pool.close()
        await self._pool.wait_closed()


class MongoDBInit:
    def __init__(self, connection_mongo: str):
        self.connection_mongo = connection_mongo
        self.client = AsyncIOMotorClient(
            self.connection_mongo, compressors='zstd,snappy,zlib')

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.client.close()


class AiobotocoreInit:
    def __init__(self):
        self.bucket = app_cfg.s3_bucket
        self.access_key = conf.s3_server['s3_access_key']
        self.secret_key = conf.s3_server['s3_secret_key']
        self.endpoint_url = f"http://{conf.s3_server['s3_server']}/"
        self.session = get_session()

    async def put_file(self, body: BytesIO, filename: str):
        await self._client.put_object(
            Bucket=self.bucket, Key=filename, Body=body.getvalue())

    async def get_file(self, filename: str) -> bytes:
        resp = await self._client.get_object(Bucket=self.bucket, Key=filename)
        data = await resp['Body'].read()

        return data

    async def list_files(self, folder_name: str):
        paginator = self._client.get_paginator('list_objects')
        async for result in paginator.paginate(
                Bucket=self.bucket, Prefix=folder_name):

            contents = list()
            for c in result.get('Contents', []):
                contents.append(c)

            return contents

    async def del_file(self, filename: str):
        resp = await self._client.delete_object(
            Bucket=self.bucket, Key=filename)
        return resp

    async def __aenter__(self):
        self._client = await self.session.create_client(
            's3', endpoint_url=self.endpoint_url,
            aws_secret_access_key=self.secret_key,
            aws_access_key_id=self.access_key).__aenter__()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.__aexit__(exc_type, exc_val, exc_tb)


def logger_initialization(path_to_logger_conf=None, log_filename=None):
    sentry_sdk.set_tag('maintainer', app_cfg.maintainer)

    if conf.docker_host:
        sentry_sdk.set_tag('docker_host', conf.docker_host)

    service_name = conf.service_name if conf.service_name else self_path.stem
    sentry_sdk.set_tag('service_name', service_name)

    project_root = get_project_root()
    logs_dir = project_root / 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    if not path_to_logger_conf:
        path_to_logger_conf = project_root / 'logging.yaml'

    if os.path.exists(Path(path_to_logger_conf)):
        with open(path_to_logger_conf, 'rt') as f:
            config = yaml.safe_load(f.read())

        config['handlers']['file']['filename'] = f'{logs_dir}/info.log'
        config['handlers']['error']['filename'] = f'{logs_dir}/error.log'
        if log_filename:
            config['handlers']['file']['filename'] = (
                f'{logs_dir}/{log_filename}_info.log')
            config['handlers']['error']['filename'] = (
                f'{logs_dir}/{log_filename}_error.log')

        logging.config.dictConfig(config)

        msgpack_kwargs = dict(default=encode_datetime)

        if conf.fluentd_host:
            from fluent import handler
            from socket import gethostname

            docker_host = (conf.docker_host if conf.docker_host
                           else gethostname())
            fluent_handler = handler.FluentHandler(
                f'log.{service_name}.{docker_host}',
                host=conf.fluentd_host,
                port=24224,
                msgpack_kwargs=msgpack_kwargs,
            )

            from traceback import format_exception

            def format_logrecord(log_record: logging.LogRecord):
                record = dict(
                    created=log_record.created,
                    filename=log_record.filename,
                    funcName=log_record.funcName,
                    module=log_record.module,
                    lineno=log_record.lineno,
                    level=log_record.levelname,
                    message=log_record.message,
                    msg=log_record.msg,
                    args=log_record.args,
                )
                if exc_info := log_record.exc_info:
                    record.update(
                        traceback=''.join(format_exception(*exc_info)))
                if extra := getattr(log_record, 'extra', None):
                    record.update(extra=extra)

                return record

            format_logrecord.usesTime = lambda: True
            fluent_handler.setFormatter(
                handler.FluentRecordFormatter(format_logrecord))
            fluent_handler.setLevel(logging.INFO)

            root = logging.getLogger()
            root.addHandler(fluent_handler)

    else:
        raise ServiceException('Файл конфигурации логгера, не задан.')


def encode_datetime(obj):
    """Сериализация в msgpack нестандартных типов"""

    if isinstance(obj, datetime):
        obj = obj.isoformat(' ')
    elif isinstance(obj, timedelta):
        obj = repr(obj)
    return obj


def get_project_root() -> Path:
    """Returns project root folder."""

    return Path(__file__).parent.parent


def check_answer_from_api(answer_api, msg_err):
    if answer_api.status_code != 200:
        msg_err = f'{msg_err}: {answer_api.text}'
        log.error(msg_err)
        answer_api.raise_for_status()

    return answer_api


def get_json_response(response):
    if 'application/json' in response.headers.get('content-type', ''):
        result = response.json()

        return result


def datetime_to_str(dt: datetime) -> str:
    date_str = dt.strftime("%d-%m-%Y")

    return date_str


def reformat_date_str(date: str) -> datetime:
    """Форматирует строковую дату дд-мм-гг в вид: datetime.date"""

    dt_date = datetime.strptime(date, '%d-%m-%Y').replace(
        second=0, minute=0, hour=0, microsecond=0)

    return dt_date
