"""Модуль настроек базы данных."""
import os

from clickhouse_driver import connect
from clickhouse_sqlalchemy import get_declarative_base, make_session
from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine

load_dotenv()

CH_DATABASE_NAME = os.getenv("CH_DATABASE_NAME")
CH_DATABASE_USER = os.getenv("CH_DATABASE_USER")
CH_DATABASE_PASSWORD = os.getenv("CH_DATABASE_PASSWORD")
CH_DATABASE_HOST = os.getenv("CH_DATABASE_HOST")
CH_DATABASE_PORT = os.getenv("CH_DATABASE_PORT")
DATABASE_URL_CH = os.getenv("DATABASE_URL_CH")
chparams = {
    "database": CH_DATABASE_NAME,
    "user": CH_DATABASE_USER,
    "password": CH_DATABASE_PASSWORD,
    "host": CH_DATABASE_HOST,
    "port": CH_DATABASE_PORT,
}

engine = create_engine(DATABASE_URL_CH)
session = make_session(engine)
metadata = MetaData(bind=engine)
Base = get_declarative_base(metadata=metadata)

connection = connect(**chparams)
cursor = connection.cursor()
