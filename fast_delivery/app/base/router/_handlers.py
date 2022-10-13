import asyncio
from collections import defaultdict
from typing import Callable, Type

from app.base.application import BaseApplication
from app.base.filler import BaseFiller
from app.base.getters import BaseGetters
from app.base.models.router import (
    CreateApplicationResponse,
    TKCreateApplicationRequest,
    TKOneIteration,
    TKOrderParams,
)
from app.base.pdf import pdf_merge
from app.base.router.protocols import RouterHandlersProtocol
from app.db import DBS
from app.exceptions import TkError
from app.settings.log import logger
from ._iteration import RouterBaseOneIteration
from ...settings import CONFIG


class RouterHandlers(RouterHandlersProtocol):
    """
    Класс для обработки заказов
    """

    def __init__(
        self,
        tk_name: str,
        filler_class: Type[BaseFiller],
        getter_class: Type[BaseGetters],
        application_class: Type[BaseApplication],
        iteration_class: Type[RouterBaseOneIteration] = RouterBaseOneIteration,
        sync_timeout=15,
        async_timeout=60,
    ):
        self.tk_name = tk_name
        self.async_timeout = async_timeout
        self.sync_timeout = sync_timeout

        self.filler_class = filler_class
        self.getter_class = getter_class
        self.iteration = iteration_class(
            filler_class=filler_class,
            getter_class=getter_class,
            application_class=application_class,
        )

    def create_application_method_async(self) -> Callable:
        """
        асинхронная версия работы с созданиями заявок
        """
        create_application_method_sync = self.create_application_method_sync()

        async def _method(task_id: str, request: TKCreateApplicationRequest):
            mongodb = DBS["mongo_epool_admin"]["client"]
            coll_name = "tk_async_tasks"
            coll = mongodb.get_collection(coll_name)
            response = await create_application_method_sync(
                request, timeout=self.async_timeout
            )
            await coll.update_one(
                {"_id": task_id}, {"$set": {"response": response.dict()}}
            )

        return _method

    def create_application_method_sync(self) -> Callable:
        """
        синхронная версия работы с созданиями заявок
        """

        async def _method(
            request: TKCreateApplicationRequest, timeout=self.sync_timeout
        ):
            mongodb = DBS["mongo_epool_admin"]["client"]
            # ответ: имя файла со всеми квитанциями и список информации по каждому заказу - ошибка или uid
            response = CreateApplicationResponse()
            # mongo collection
            coll_name = f"tk_{self.tk_name}" + ("" if not request.test else "_test")
            mng_coll = mongodb.get_collection(coll_name)
            # список заказов с параметрами для печати
            orders = []
            success_orders = defaultdict(list)

            for order_params in request.arr:  # type: TKOrderParams
                orders += [
                    self.iteration.iterate(
                        order_params, mng_coll, test=request.test, timeout=timeout
                    )
                ]

            for i, item in enumerate(
                await asyncio.gather(*orders, return_exceptions=not CONFIG["test"])
            ):  # type: TKOneIteration
                idmonopolia = request.arr[i].id
                if isinstance(item, Exception):
                    logger.error(
                        f"Ошибка сервиса: {item}. Подробности в логах", exc_info=True
                    )
                    logger.exception(item)
                    response.info.append(
                        TkError(id=idmonopolia, error="Ошибка сервиса")
                    )
                    continue

                logger.info(
                    f"Результат асинхронной обработки заявки idmonopolia={idmonopolia}: is_success={item.is_success}"
                    f" response={item.response}"
                )
                response.info.append(item.response)
                if item.is_success:
                    success_orders["orders"] += [item.response]

                    if not item.response.error:
                        success_orders["orders_with_pdf"] += [item.response]
                        success_orders["pdf_cargo"] += [item.pdf.cargo]
                        success_orders["pdf_info"] += [item.pdf.info]

            await pdf_merge(response, success_orders, self.tk_name)
            return response

        return _method
