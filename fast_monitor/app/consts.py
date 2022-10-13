#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

SERVICE_NAME = "fast_monitor"
VERSION = 'v1'

ROOT_DIR = Path(__name__).parent.parent.absolute()

ENV_FILE = ROOT_DIR / ".env"
LOGS_DIR = ROOT_DIR / 'logs'
FONTS_DIR = ROOT_DIR / 'fonts'

API_PREFECT_URL = 'https://api.prefect.io/graphql'
