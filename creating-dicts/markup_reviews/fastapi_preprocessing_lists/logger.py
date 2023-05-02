"""Конфигурация логгера."""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    filename="program.log",
    format="%(asctime)s, %(levelname)s, %(message)s, %(name)s",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s"
)
handler.setFormatter(formatter)
