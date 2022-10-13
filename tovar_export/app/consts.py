#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

SERVICE_NAME = "tovar_export"
VERSION = 'v1'

ROOT_DIR = Path(__name__).parent.parent.absolute()

ENV_FILE = ROOT_DIR / ".env"
LOGS_DIR = ROOT_DIR / 'logs'
