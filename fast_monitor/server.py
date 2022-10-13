import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.responses import Response
from app.get_monitor import build_monitor
from app.tools import init_logging
from app.env_conf import SETTINGS
from app.get_chart import build_chart
from app.db import init_databases, shutdown_databases

router = APIRouter()


@router.on_event("startup")
async def startup():
    await init_databases(SETTINGS, clickhouse=True)


@router.on_event("shutdown")
async def shutdown():
    await shutdown_databases()


@router.get("/self_check")
async def self_check():
    """ \n
     Функция для проверки работоспособности всего микросервиса
        - На вход ничего не поступает
        - Возвращает просто словарь с ключем "status" и значением "Ok"
    """

    return {"status": "Ok"}


@router.get('/get_monitor')
async def get_monitor():
    """ \n
     Функция для отрисовки картинки о состоянии работы микросервисов
        - На вход ничего не поступает
        - Возвращает картинку с размером 1366х768 в формате PNG
    """

    img = await build_monitor()
    return Response(content=img, media_type="image/PNG")


@router.get("/get_chart")
async def get_chart():
    """ \n
     Функция для отрисовки графика
        - По оси абсцисс располагается суточное время
        - По оси ординат расплагается время ответа сервиса
        - Точки на графике - это кол-во запросов к сервису
        - Красные точки в верху графика - это запросы, у которых время запроса превысило 3 секунды
        - На вход ничего не поступает
        - Возвращает картинку с размером 1800x600 в формате PNG
    """

    chart = await build_chart()
    return Response(content=chart, media_type="image/PNG")


def init_app(use_sentry=True):
    init_logging(use_sentry=use_sentry)

    app = FastAPI()

    app.include_router(router)
    return app


def run():
    app = init_app(use_sentry=not SETTINGS.DEBUG)
    uvicorn.run(app, host="0.0.0.0", port=7777)


if __name__ == "__main__":
    run()
