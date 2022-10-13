import asyncio
from datetime import datetime
from typing import Type, Optional, Union

from motor.motor_asyncio import AsyncIOMotorCollection

from app.base.application import BaseApplication
from app.base.filler import BaseFiller
from app.base.getters import BaseGetters
from app.base.models.router import TKOneIteration, TKOrderParams, CreateApplicationInfo
from app.exceptions import (
    FillerException,
    TkError,
    TransportAPIException,
    TransportAPITimeOutException,
)
from app.settings import CONFIG
from app.settings.log import logger
from .protocols import RouterOneIterationProtocol


class RouterBaseOneIteration(RouterOneIterationProtocol):
    """
    Класс для обработки одного заказа
    """

    def __init__(
        self,
        application_class: Type[BaseApplication],
        filler_class: Type[BaseFiller],
        getter_class: Type[BaseGetters],
    ):
        self.application_class = application_class
        self.filler_class = filler_class
        self.getter_class = getter_class

    async def iterate(
        self,
        order_params: TKOrderParams,
        mng_coll: AsyncIOMotorCollection,
        test=False,
        timeout=10,
    ) -> TKOneIteration:
        iteration = TKOneIteration()
        parameters, resp = await self.get_application_params(order_params, test)

        if not resp:
            application = self.application_class(
                order_params,
                parameters,
                test=test,
                force=order_params.force,
                timeout=timeout,
            )
            await self.load_application(application, mng_coll, order_params)
            resp = await self.push_application_tk(
                iteration, order_params, application, mng_coll
            )
            if not resp.error:
                await self.create_application_docs(iteration, application, resp)
        iteration.response = resp
        return iteration

    async def get_application_params(
        self, order_params: TKOrderParams, test=False
    ) -> tuple[dict, Optional[TkError]]:
        error_resp, parameters = None, None
        # получаем шаблон заявки для предрегистрации (с заполненными общими полями)
        filler = self.filler_class(
            order_params=order_params, getter_class=self.getter_class, test=test
        )
        # дополняем шаблон заявки данными из баз данных
        try:
            # дополняем шаблон заявки на забор груза параметрами
            parameters = await filler.get_parameters()
        except FillerException as e:
            _r = {"id": order_params.id, "error": str(e)}
            logger.error(f"Заказ {_r['id']}: {_r['error']}", exc_info=True)
            error_resp = TkError(**_r)
        except Exception as e:
            _r = {"id": order_params.id, "error": str(e)}
            if CONFIG["test"]:
                raise e
            logger.error(
                f"Заказ {_r['id']} не создан по причине внутренней ошибки: {_r['error']}",
                exc_info=True,
            )
            error_resp = TkError(**_r)
        return parameters, error_resp

    async def load_application(
        self,
        application: BaseApplication,
        mng_coll: AsyncIOMotorCollection,
        order_params: TKOrderParams,
    ) -> None:
        # получаем заявку из монго, если мы ее туда уже сохраняли
        if order_params.force:
            await mng_coll.delete_one({"_id": order_params.id})
        r = await mng_coll.find_one({"_id": order_params.id})
        if r:
            if resp := r.get("response"):
                # Поддержка ПЭК
                if "error" not in resp:
                    application.load(resp)
            elif r.get("cargos"):
                application.load(r)

    async def push_application_tk(
        self,
        iteration: TKOneIteration,
        order_params: TKOrderParams,
        application: BaseApplication,
        mng_coll: AsyncIOMotorCollection,
    ) -> Union[TkError, CreateApplicationInfo]:
        is_error = True
        response = None
        try:
            if application.is_loaded():
                logger.info(
                    f"Параметры для заказа idmonopolia={order_params.id} заружены из БД"
                )
            else:
                logger.info(
                    f"Заказ idmonopolia={order_params.id} отправлен на создание в ТК",
                )
                response = await application.create()
                mng = {
                    "_id": order_params.id,
                    "request_params": order_params.dict(),
                    "order_params": application.tk_parameters,
                    "date": datetime.now(),
                    "response": response,
                }
                # и записываем в монгу. Чтобы несколько заявок по одному заказу не делать
                await mng_coll.update_one(
                    {"_id": mng["_id"]}, {"$set": mng}, upsert=True
                )
            # дописываем номер накладной в ответ
            resp = CreateApplicationInfo(
                id=order_params.id, tk_num=await application.get_order_num()
            )

            iteration.is_success = True
            is_error = False
        except TransportAPIException as e:
            _r = {
                "id": order_params.id,
                "error": f"не создан по причине ошибки ТК. Ошибка: {e}",
            }
            logger.error(f"Заказ {_r['id']}: {_r['error']}", exc_info=True)
            resp = TkError(**_r)
        except TransportAPITimeOutException as e:
            _r = {
                "id": order_params.id,
                "error": f"отправлен на обработку, но информацию не удалось получить: {e}",
            }
            logger.error(f"Заказ {_r['id']}: {_r['error']}", exc_info=True)
            resp = TkError(**_r)
        except Exception as e:
            _r = {"id": order_params.id, "error": f"Ошибка в сервисе. Error: {e}"}
            logger.error(
                f"Заказ {_r['id']} не создан по причине внутренней ошибки: {_r['error']}",
                exc_info=True,
            )
            if CONFIG["test"]:
                raise e
            logger.exception(e)
            resp = TkError(**_r)

        if is_error:
            if not response:
                response = {"error": "Ошибка, связанная с получением данных для заявки"}
            mng = {
                "_id": order_params.id,
                "request_params": order_params.dict(),
                "order_params": application.tk_parameters,
                "date": datetime.now(),
                "response": response,
                "is_error": True,
            }
            await mng_coll.update_one({"_id": mng["_id"]}, {"$set": mng}, upsert=True)
        return resp

    async def create_application_docs(
        self,
        iteration: TKOneIteration,
        application: BaseApplication,
        resp: CreateApplicationInfo,
    ) -> None:
        idmonopolia = application.order_parameters.id
        pdf_future = asyncio.gather(
            application.get_pdf("info"), application.get_pdf("cargo")
        )
        try:
            pdf = await pdf_future
            iteration.pdf.info = pdf[0]
            iteration.pdf.cargo = await application.modify_pdf(
                "cargo", pdf[1], idmonopolia
            )
        except TimeoutError as e:
            pdf_future.cancel()
            resp.error = (
                "Не удалось получить PDF: истекло время подключения к сервису TK."
            )
        except Exception as e:
            pdf_future.cancel()
            _r = {
                "id": idmonopolia,
                "error": f"не успели создасться PDF, попробуйте еще раз позже: {e}",
            }
            logger.error(f"Заказ {_r['id']}: {_r['error']}", exc_info=True)
            resp.error = "Не успели создаться pdf, попробуйте позже."
