from typing import Protocol, Awaitable, Callable, Optional, Union

from fastapi import APIRouter
from motor.motor_asyncio import AsyncIOMotorCollection

from app.base.application import BaseApplication
from app.base.models.router import TKOneIteration, TKOrderParams, CreateApplicationInfo
from app.exceptions import TkError


class RouterHandlersProtocol(Protocol):
    """
    интерфейс для обработкии заказов
    """

    def create_application_method_async(self) -> Callable:
        ...

    def create_application_method_sync(self) -> Callable:
        ...


class RouterEndpointsProtocol(Protocol):
    """
    интерфейс для эндпойнтов
    """

    def create_router(self) -> APIRouter:
        ...

    def get_create_application_sync_endpoint(self) -> Awaitable:
        ...

    def get_create_application_async_endpoint(self) -> Awaitable:
        ...

    def get_check_application_async_endpoint(self) -> Awaitable:
        ...


class RouterOneIterationProtocol(Protocol):
    """
    интерфейс для обработки одного заказа
    """

    async def iterate(
        self,
        order_params: TKOrderParams,
        mng_coll: AsyncIOMotorCollection,
        test=False,
        timeout=10,
    ) -> TKOneIteration:
        ...

    async def get_application_params(
        self, order_params: TKOrderParams, test=False
    ) -> tuple[dict, Optional[TkError]]:
        ...

    async def load_application(
        self,
        application: BaseApplication,
        mng_coll: AsyncIOMotorCollection,
        order_params: TKOrderParams,
    ) -> None:
        ...

    async def push_application_tk(
        self,
        iteration: TKOneIteration,
        order_params: TKOrderParams,
        application: BaseApplication,
        mng_coll: AsyncIOMotorCollection,
    ) -> Union[TkError, CreateApplicationInfo]:
        ...

    async def create_application_docs(
        self,
        iteration: TKOneIteration,
        application: BaseApplication,
        resp: CreateApplicationInfo,
    ) -> None:
        ...
