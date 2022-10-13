from datetime import datetime
from typing import Type, Optional

from bson import ObjectId
from fastapi import HTTPException, APIRouter, status
from pydantic import BaseModel
from starlette.background import BackgroundTasks
from starlette.requests import Request
from starlette.responses import Response

from app.base.models.router import (
    CreateApplicationResponse,
    TKCreateApplicationAsync,
    TKCreateApplicationRequest,
)
from app.base.router.protocols import RouterEndpointsProtocol, RouterHandlersProtocol
from app.base.router.utils import cargopick_checker, null_data_checker
from app.base.status_updater import TKStatusUpdater
from app.db import DBS
from app.repeat_every import repeat_every
from app.settings import CONFIG
from app.settings.consts import STATUS_UPDATE_CYCLE
from app.settings.log import logger, format_log_message


class RouterEndpoints(RouterEndpointsProtocol):
    """
    Класс для создания эндпойнтов
    """

    sync_timeout = 20
    async_timeout = 60

    def __init__(
        self,
        router_prefix: str,
        handlers: RouterHandlersProtocol,
        create_application_request_model: Type[BaseModel] = TKCreateApplicationRequest,
        create_application_response_model: Type[BaseModel] = CreateApplicationResponse,
        status_updater: Optional[TKStatusUpdater] = None,
        startup=None,
    ):
        """
        @param router_prefix: префикс для роутера
        @param handlers: класс с обработкой заявок
        @param create_application_request_model: модель запроса к эндпойту создания заявки
        @param create_application_response_model: модель ответа эндпойта создания заявки
        """
        self.handlers = handlers
        self.router_prefix = router_prefix
        self.create_application_request_model = create_application_request_model
        self.create_application_response_model = create_application_response_model
        self.status_updater = status_updater
        self.startup = startup

    def create_router(self):
        router_prefix = self.router_prefix
        router = APIRouter()

        router.post(
            f"/{router_prefix}/create_application/",
            response_model=CreateApplicationResponse,
        )(self.get_create_application_sync_endpoint())

        router.post(
            f"/{router_prefix}/create_application_async/",
            response_model=TKCreateApplicationAsync,
        )(self.get_create_application_async_endpoint())

        router.post(
            f"/{router_prefix}/check_application_async/",
            response_model=CreateApplicationResponse,
        )(self.get_check_application_async_endpoint())

        startup_f = []

        if self.startup:
            startup_f += [self.startup]

        if self.status_updater:
            startup_f += [self.get_status_checker_worker()]

        if startup_f:

            async def m():
                for f in startup_f:
                    await f()

            router.on_event("startup")(m)

        return router

    def get_create_application_sync_endpoint(self):
        create_application_method_sync = self.handlers.create_application_method_sync()
        create_application_request_model = self.create_application_request_model
        create_application_response_model = self.create_application_response_model

        async def _method(
            _request: Request,
            _response: Response,
            request: create_application_request_model,
        ) -> create_application_response_model:
            logger.info(await format_log_message(_request, {}, has_body=True))
            await cargopick_checker(_request, request)
            await null_data_checker(_request, request)
            response = await create_application_method_sync(
                request, timeout=self.sync_timeout
            )
            logger.info(
                await format_log_message(_request, response.dict(), has_body=True)
            )
            return response

        return _method

    def get_create_application_async_endpoint(self):
        create_application_method_async = (
            self.handlers.create_application_method_async()
        )
        create_application_request_model = self.create_application_request_model

        async def _method(
            _request: Request,
            request: create_application_request_model,
            background_tasks: BackgroundTasks,
        ) -> TKCreateApplicationAsync:
            logger.info(await format_log_message(_request, {}, has_body=True))
            await cargopick_checker(_request, request)
            await null_data_checker(_request, request)

            mongodb = DBS["mongo_epool_admin"]["client"]
            coll_name = "tk_async_tasks"
            coll = mongodb.get_collection(coll_name)

            task_id = await coll.insert_one({"request": request.dict()})
            token_str = str(task_id.inserted_id)
            background_tasks.add_task(
                create_application_method_async, token_str, request
            )
            response = TKCreateApplicationAsync(token=token_str)
            logger.info(
                await format_log_message(_request, response.dict(), has_body=True)
            )
            return response

        return _method

    def get_check_application_async_endpoint(self):
        create_application_response_model = self.create_application_response_model

        async def _method(
            request: TKCreateApplicationAsync,
        ) -> create_application_response_model:
            mongodb = DBS["mongo_epool_admin"]["client"]
            coll_name = "tk_async_tasks"
            coll = mongodb.get_collection(coll_name)

            task = await coll.find_one({"_id": ObjectId(request.token)})
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Задача c token={request.token} не найдена",
                )
            if response := task.get("response"):
                return CreateApplicationResponse(**response)
            raise HTTPException(
                status_code=status.HTTP_201_CREATED,
                detail=f"Задача c token={request.token} не готова",
            )

        return _method

    def get_status_checker_worker(self):
        async def _status_updater():
            if CONFIG["is_update_statuses"]:
                logger.warning(
                    f"Обновление статусов {self.router_prefix}: {datetime.now()}"
                )
                try:
                    await self.status_updater.update_all(test=CONFIG["test"])
                except Exception as e:
                    logger.exception(e)
                    if CONFIG["test"]:
                        raise e

        return repeat_every(seconds=STATUS_UPDATE_CYCLE)(_status_updater)
