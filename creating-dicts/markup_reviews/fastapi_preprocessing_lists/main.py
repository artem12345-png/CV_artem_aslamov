import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi_pagination import add_pagination
from logger import logger
from result_dicts import dict_router
from result_dicts.settings.exceptions import NotAuthenticatedException


def create_app():
    """Инициализация приложения fastapi."""

    app = FastAPI()
    app.include_router(dict_router.router)
    logger.info("Инициализация FastApi прошла успешно")
    return app


app = create_app()
add_pagination(app)


@app.exception_handler(NotAuthenticatedException)
def auth_exception_handler(request: Request, exc: NotAuthenticatedException):
    """
    Redirect the user to the login page if not logged in
    """
    return RedirectResponse(url="/login")


if __name__ == "__main__":
    logger.info("Старт FastApi")
    uvicorn.run("main:app", host="localhost", port=8078, reload=True)
