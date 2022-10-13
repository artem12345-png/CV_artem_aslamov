from fastapi import Request
from pathlib import Path
from typing import Optional

import sentry_sdk
import yaml
import logging.config as lcfg
import logging

from .consts import VERSION, ROOT_DIR
from ..env import SETTINGS, SERVICE_NAME

logger = logging.getLogger(name=SERVICE_NAME)


def init_logging(self_path: Optional[Path] = ROOT_DIR, use_sentry=True):
    conf_log_path = self_path / "logging.yaml"
    conf = yaml.full_load(conf_log_path.open())
    lcfg.dictConfig(conf["logging"])

    dsn = (conf.get("sentry") or {}).get("dsn")
    if dsn and use_sentry:
        sentry_sdk.init(dsn=dsn, release=f"{SERVICE_NAME}@{VERSION}")

    sentry_sdk.set_tag("maintainer", "Aslamov and Karasyuk")
    sentry_sdk.set_tag("service_name", SERVICE_NAME)
    docker_host = SETTINGS.DOCKER_HOST
    routing_name = (
        f"log.{SERVICE_NAME}.{docker_host}" if docker_host else f"log.{SERVICE_NAME}"
    )
    print(routing_name)
    if docker_host:
        sentry_sdk.set_tag("docker_host", docker_host)
    if service_name := SETTINGS.SERVICE_NAME:
        sentry_sdk.set_tag("service_name", service_name)


async def format_log_message(request: Request, response=None, has_body=True):
    m = f"{request.url.path} "
    if has_body:
        m += f"body: {await request.json()} "

    if response:
        m += f"response: {response} "
    return m
