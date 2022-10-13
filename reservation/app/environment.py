import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional
from logging import config as lcfg
import aiomysql
import cx_Oracle_async
import sentry_sdk
import yaml
from pydantic import BaseSettings
from app.consts import ROOT_DIR, SERVICE_NAME, VERSION


class ApplicationSettings(BaseSettings):
    service_name_oracle: str | None
    oracle_connect: dict | None
    mysql_connect: dict | None
    DOCKER_HOST: str | None
    TEST: int | None

    class Config:
        env_file = ".env"


class SingletonMeta(type):
    """
    Метакласс для реализации паттерна одиночки.
    При попытки создания нового экземпляра класса
    будет возвращаться уже инициализированный объект.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


@lru_cache()
def get_settings():
    """
    Для тестового окружения можно менять эту функцию
    """
    return ApplicationSettings()


class DBOraclePool(metaclass=SingletonMeta):
    def __init__(self):
        self.pool = None

    async def get_pool(self) -> None:
        logger.info("Создаётся пул соединений к Oracle DB")
        settings = get_settings()

        oracle_conn = settings.oracle_connect
        hosts = oracle_conn["hosts"]
        port = oracle_conn["port"]
        addresses = "\n".join(
            [f"(ADDRESS = (PROTOCOL = TCP)(HOST = {i})(Port={port}))" for i in hosts]
        )
        DSN = f"""
               (DESCRIPTION =
                 {addresses}
                 (CONNECT_DATA =
                   (SID = {settings.service_name_oracle})
                 )
               )
            """
        user = oracle_conn["user"]
        password = oracle_conn["password"]
        self.pool = await cx_Oracle_async.create_pool(
            user=user, password=password, dsn=DSN
        )
        logger.info("Пул соединений к Oracle DB создан")

    async def get_connection(self):
        if self.pool is None:
            await self.get_pool()

        async with self.pool.acquire() as connection:
            logger.info("Создан коннект")
            yield connection
            logger.info("Коннект закрыт")

    async def close(self):
        logger.info("Закрытие пула соединений...")
        await self.pool.close()
        logger.info("Пулл соединений закрыт")


class DBMySQLPool(metaclass=SingletonMeta):
    def __init__(self):
        self.pool = None

    async def get_pool(self) -> None:
        logger.info("Создаётся пул соединений к MySQL")
        settings = get_settings()

        mysql_conn = settings.mysql_connect

        mysql_host = mysql_conn["host"]
        mysql_user = mysql_conn["user"]
        mysql_pass = mysql_conn["password"]
        mysql_db = mysql_conn["db"]

        self.pool = await aiomysql.create_pool(
            minsize=0,
            maxsize=5,
            autocommit=True,
            pool_recycle=10,
            host=mysql_host,
            user=mysql_user,
            password=mysql_pass,
            db=mysql_db,
        )
        logger.info("Пул соединений к MySQL создан")

    async def get_connection(self):
        if self.pool is None:
            await self.get_pool()

        async with self.pool.acquire() as connection:
            logger.info("Создан коннект")
            yield connection
            logger.info("Коннект закрыт")

    async def close(self):
        logger.info("Закрытие пула соединений...")
        await self.pool.close()
        logger.info("Пулл соединений закрыт")


def init_logging(self_path: Optional[Path] = ROOT_DIR, use_sentry=True):
    env = get_settings().dict().get
    from socket import gethostname

    docker_host = env("DOCKER_HOST") or gethostname()
    routing_name = (
        f"log.{SERVICE_NAME}.{docker_host}" if docker_host else f"log.{SERVICE_NAME}"
    )
    print(routing_name)

    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir()

    conf_log_path = self_path / "logging.yaml"
    conf = yaml.full_load(conf_log_path.open())
    lcfg.dictConfig(conf["logging"])

    dsn = conf["sentry"]["dsn"]
    if dsn and use_sentry:
        sentry_sdk.init(dsn=dsn, release=f"{SERVICE_NAME}@{VERSION}")

    sentry_sdk.set_tag("maintainer", "Aslamov")
    sentry_sdk.set_tag("service_name", SERVICE_NAME)
    if docker_host := env("DOCKER_HOST"):
        sentry_sdk.set_tag("docker_host", docker_host)


logger = logging.getLogger(name=SERVICE_NAME)
