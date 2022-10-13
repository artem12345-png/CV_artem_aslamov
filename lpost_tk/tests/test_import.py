#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import app.configs.app_conf
import app.configs.env_conf
import app.main
import app.tools
from app.tools import get_project_root, logger_initialization


def test_test():
    pass


def test_logging():
    logger_initialization(
        path_to_logger_conf=f'{get_project_root()}/deploy/logging_deploy.yaml'
    )
