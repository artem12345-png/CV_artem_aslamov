from abc import abstractmethod
from typing import Protocol, Type

from app.base.getters import (
    BaseGetters,
    CargoBaseGetter,
    ReceiverBaseGetter,
    SenderBaseGetter,
)
from app.db import DBS
from app.base.models.router import TKOrderParams
from app.delivery_calc import DeliveryCalcWrapper
from app.delivery_calc.models import DeliveryCalcRequest, DeliveryCalcResponse
from app.exceptions import FillerException
from app.utils import delete_none


class FillerProtocol(Protocol):
    async def get_parameters(self) -> dict:
        ...


class BaseFiller(FillerProtocol):
    """
    Класс хранит в себе все данные по idmonopolia из базы.
    Данные берутся с помощью функции _get_db_data.
    Когда мы определяем филлер - вызов _get_db_data гарантируется.
    """
    _db_data = None
    base_cargo: CargoBaseGetter = None
    base_sender: SenderBaseGetter = None
    base_receiver: ReceiverBaseGetter = None
    calc_delivery_resp: DeliveryCalcResponse = None
    # переопределяем при наследовании
    tk_id: int = None

    order_params: TKOrderParams

    def __init__(
        self, order_params: TKOrderParams, getter_class: Type[BaseGetters], test=False
    ):
        self.order_params = order_params
        self.getter_class = getter_class
        self.test = test

    async def _get_db_data(self, getter_class):
        getter: BaseGetters = getter_class(self.order_params.id)
        self._db_data = await getter.get_database_data()
        self.base_cargo = await getter.get_cargo_data()
        self.base_sender = await getter.get_sender_data()
        self.base_receiver = await getter.get_receiver_data()

    async def get_parameters(self) -> dict:
        await self._get_db_data(self.getter_class)
        result = await self.fill()
        result = delete_none(result.dict(exclude_none=True))
        return result

    @abstractmethod
    async def fill(self):
        """Данный метод должен возвращать заполненную заявку для данной ТК"""
        pass

    async def _calc_delivery(self) -> DeliveryCalcResponse:
        """Рассчитывается стоимость доставки для данной заявки"""
        assert self.tk_id is not None, "Не указан номер ТК"
        if self.calc_delivery_resp:
            return self.calc_delivery_resp

        del_calc: DeliveryCalcWrapper = DBS["delivery_calc"]
        goods = [
            DeliveryCalcRequest.Good(
                gid=good.idgood,
                amount=good.quantity,
                owersize=self.base_cargo.oversized,
                **good.dict(),
            )
            for good in self.base_cargo.cargos
        ]

        NeedCalc = DeliveryCalcRequest.NeedCalc
        need_calc = (
            NeedCalc.to_addr if self.base_receiver.is_delivery else NeedCalc.to_term
        )
        req = DeliveryCalcRequest(
            idmon=self.order_params.id,
            cost=self.base_cargo.sum_price,
            to_kladr=self.base_receiver.dadata.kladr_id,
            to_city=self.base_receiver.city,
            goods=goods,
            need_calc=need_calc,
            # TODO: не только из МСК
            # alias в pydantic и служебное слово "from" требуют костыля
            **{"from": "msk"},
        )
        try:
            self.calc_delivery_resp = await del_calc.calc_tk(
                tk_id=self.tk_id, data=req, test=self.test
            )
        except Exception as e:
            raise FillerException(
                f"Не удалось рассчитать стоимость доставки. Причина: {e}"
            )
        return self.calc_delivery_resp

    async def _get_delivery_sum(self):
        resp = await self._calc_delivery()
        return resp.price

    async def _get_delivery_tariff_code(self):
        resp = await self._calc_delivery()
        return resp.tariff_code
