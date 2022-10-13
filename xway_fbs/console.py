"""
Запускает скрипт из папки scripts, инициалиируя всё по пути.
Чтобы запустить скрипт - необходимо, чтобы в нём была функция main
"""

import asyncio
import importlib
import inspect

import click

from ozon.tools import logger, init_logging, init_dbs, disconnect_dbs

SCRIPTS_DIR = "scripts"


@click.command()
@click.option("--script", prompt="Script's name")
def main(script):
    """
    Пример запуска python3 console.py --script=check_duplicates
    удобно настроить конфигурацию в пайчарм
    """
    asyncio.run(console(script))


async def console(script):
    logger.info(f"Идет запуск скрипта {script}...")
    assert not script.endswith(".py"), "Передайте название файла без расширения"
    await init_dbs()
    init_logging(use_sentry=True)
    try:
        logger.info(f"Идет запуск скрипта {script}..")
        mod = importlib.import_module(f"{SCRIPTS_DIR}.{script}")

        # предполагаем, что основная функция в каждом из сккриптов называется `main`
        await start_func(mod.main)
    except Exception as e:
        logger.error(f"Скрипт {script} закончил свою работу с ошибкой: {e}")
    finally:
        logger.info(f"Скрипт {script} закончил свою работу")
        await disconnect_dbs()


async def start_func(f):
    # Проверка функции на асинхронность
    if inspect.iscoroutinefunction(f):
        await f()
    else:
        f()


if __name__ == "__main__":
    main()
