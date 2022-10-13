from app.consts import LOGS_DIR, ROOT_DIR, SERVICE_NAME, VERSION
from app.env_conf import SETTINGS
import logging
import logging.config
import sentry_sdk
import yaml
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(SERVICE_NAME)


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