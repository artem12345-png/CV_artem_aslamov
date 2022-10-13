#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

# import sentry_sdk
import uvicorn
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from app.configs.app_conf import app_cfg
# from app.configs.env_conf import conf
from app.main import app
from app.tools import logger_initialization

log = logging.getLogger(__name__)
# sentry_sdk.init(
#     dsn=conf.sentry_dsn,
#     traces_sample_rate=app_cfg.sentry_sample_rate,
#     sample_rate=app_cfg.sentry_sample_rate)

asgi_app = SentryAsgiMiddleware(app)


def run():
    logger_initialization()
    log.info('Service is started.')
    uvicorn.run(asgi_app, host=app_cfg.local_host, port=app_cfg.port)


if __name__ == '__main__':
    run()
    log.info('*** Service is shutdown. ***')
