#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import logging.config
import os
from datetime import datetime, timedelta
from pathlib import Path
from traceback import format_exception
from typing import Optional
import asyncio
import sentry_sdk
import yaml
from fluent import handler
# from gql import gql, Client
# from gql.transport.requests import RequestsHTTPTransport
import aiohttp
from aiographql.client import GraphQLClient, GraphQLRequest
from app.consts import (
    SERVICE_NAME, VERSION, ROOT_DIR, LOGS_DIR, API_PREFECT_URL)
import httpx
from app.env_conf import SETTINGS

logger = logging.getLogger(SERVICE_NAME)


async def conection(api_token):
    async with aiohttp.ClientSession() as Session:
        client = await get_gql_client(api_token, Session)
        access_token = await get_access_token(client, Session)
        client = await get_gql_client(access_token, Session)
        r = await get_information(client, Session)
    return r


async def get_information(client, Session):
    query = """
    {
          flow(
            where: {flow_runs:{}}
            order_by: {version: desc}) {
            name
            flow_runs(
              where: {state: {_eq: "Scheduled"}}
              order_by: {start_time: desc}
              limit: 1
            ) {
              state
            }
          }
        }
    """
    response = await client.query(request=query, session=Session)


    # Отбираем имена потоков запускающихся по расписанию.
    flow_names = [e['name'] for e in response.data['flow'] if
                  e['flow_runs'] and e['flow_runs'][0][
                      'state'] == 'Scheduled']

    query = """
    {
          flow(
            where: {flow_runs:{}}
            order_by: {version: desc}) {
            name
            flow_runs(
              where: {state: {_neq: "Scheduled"}}
              order_by: {end_time: desc}
              limit: 1
            ) {
              state
              start_time
              end_time
            }
          }
        }
    """
    response = await client.query(request=query, session=Session)

    statuses = list()
    for fn in flow_names:
        for e in response.data['flow']:
            fr = e['flow_runs'][0] if e['flow_runs'] else {}
            if fn == e['name'] and fr.get('end_time'):
                statuses.append(
                    {
                        'friendly_name': fn,
                        'status': fr['state'],
                        'end_time': fr['end_time']
                    })
                break

    return statuses


async def get_gql_client(api_token, Session):
    client = GraphQLClient(
        endpoint="https://api.prefect.io/graphql",
        headers={"Authorization": f"Bearer {api_token}"},
        session=Session
    )
    return client


async def get_access_token(client, Session):
    tenant_id = """
    query {
        tenant(order_by: {slug: asc}) {
            id
            slug
            name
        }
    }
    """

    response = await client.query(request=tenant_id, session=Session)
    tenant_id = response.data['tenant'][0]['id']
    print(tenant_id)
    response = await client.query(request="""
    mutation($input: switch_tenant_input!) {
        switch_tenant(input: $input) {
            expires_at
            refresh_token
            access_token
        }
    }
    """, variables=dict(input=dict(tenant_id=tenant_id)), session=Session)
    access_token = response.data['switch_tenant']['access_token']

    return access_token



def init_logging(use_sentry=True, self_path: Optional[Path] = ROOT_DIR):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    routing_name = (
        f"log.{SERVICE_NAME}.{SETTINGS.DOCKER_HOST}" if SETTINGS.DOCKER_HOST
        else f"log.{SERVICE_NAME}")

    conf_log_path = self_path / 'logging.yaml'
    conf = yaml.full_load(conf_log_path.open())
    logging.config.dictConfig(conf['logging'])

    if use_sentry and SETTINGS.SENTRY_DSN:
        sentry_sdk.init(dsn=SETTINGS.SENTRY_DSN, release=f"{SERVICE_NAME}@{VERSION}")

    if SETTINGS.DOCKER_HOST:
        sentry_sdk.set_tag('DOCKER_HOST', SETTINGS.DOCKER_HOST)

    sentry_sdk.set_tag('service_name', SERVICE_NAME)
    sentry_sdk.set_tag("maintainer", "aslamov")

    def encode_datetime(obj):
        """Сериализация в msgpack нестандартных типов"""
        if isinstance(obj, datetime):
            obj = obj.isoformat(' ')
        elif isinstance(obj, timedelta):
            obj = repr(obj)
        return obj

    msgpack_kwargs = dict(default=encode_datetime)
    if SETTINGS.FLUENTD_HOST:
        fluent_handler = handler.FluentHandler(
            routing_name, host=SETTINGS.FLUENTD_HOST, port=24224,
            msgpack_kwargs=msgpack_kwargs)

        def format_logrecord(log_record: logging.LogRecord):
            record = dict(
                created=log_record.created,
                filename=log_record.filename,
                funcName=log_record.funcName,
                module=log_record.module,
                lineno=log_record.lineno,
                level=log_record.levelname,
                message=log_record.message,
                msg=log_record.msg, args=log_record.args, )
            exc_info = log_record.exc_info
            if exc_info:
                record.update(traceback=''.join(format_exception(*exc_info)))
            extra = getattr(log_record, 'extra', None)
            if extra:
                record.update(extra=extra)

            return record

        format_logrecord.usesTime = lambda: True
        fluent_handler.setFormatter(handler.FluentRecordFormatter(
            format_logrecord))
        fluent_handler.setLevel(logging.INFO)

        root = logging.getLogger()
        root.addHandler(fluent_handler)
