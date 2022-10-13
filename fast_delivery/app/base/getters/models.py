from typing import Optional, Union

from pydantic import BaseModel, Field

from app.db.models import (
    EpZakazMon4tkMySql,
    EpoolTerminalsMongo,
    DadataCleanModel,
    PrGoodsMySql,
    PrGoodSizesMySql,
    EPZakazMySQL,
)


class BaseGetter(BaseModel):
    phone: str = ""
    city: str = ""
    person: str = ""
    address: str = ""
    title: str = ""
    inn: str = ""
    email: Optional[str] = ""
    dadata: Optional[DadataCleanModel]


class SenderBaseGetter(BaseGetter):
    warehouse_num: int = None


class ReceiverBaseGetter(BaseGetter):
    is_delivery: bool = True
    passport: str = ""
    tk_uuid: str = ""
    idbuyer: int = None


class GoodServices(BaseModel):
    """
    Класс с дополнительной информацией по товару
    в CargoBaseGetter имеет смысл: если хоть один груз, к примеру, хрупкий, то все остальные считаются тоже
    """

    fragile: bool = False  # хрупкий ли товар
    warm_car: bool = False  # нужен ли теплый вагон для товара
    oversized: bool = False  # негабаритный ли товар


class CargoBaseItemGetter(GoodServices):
    idgood: int
    title: str
    price: int
    quantity: int = 1
    weight: float = 0.5
    volume: float = 0.1
    length: float = 0
    width: float = 0
    height: float = 0


class CargoBaseGetter(GoodServices):
    cargos: list[CargoBaseItemGetter] = Field(default_factory=list)
    sum_price: int = 0
    sum_weight: float = 0.5
    sum_volume: float = 0.1
    max_width: float = 0.1
    max_length: float = 0.1
    max_height: float = 0.1


class CargoQueryRes(PrGoodsMySql, PrGoodSizesMySql):
    idgood: Optional[int]
    iditem: Optional[int]


class MonopoliaOrder(BaseModel):
    """
    используется как для таблицы ep_zakaz_monopolia, так и для ep_zakaz_parts
    """

    idgood: int
    amount: int
    price: int


class DeliveryParameters(BaseModel):
    """Поля, которые используются при заполнении заявки, но не вытаскиваются из баз."""

    is_avia: bool = Field(False, description="Требуется ли авиаперевозка")


class DatabaseData(BaseModel):
    idmonopolia: int
    mon4tk: EpZakazMon4tkMySql
    ep_zakaz: EPZakazMySQL
    epool_terminal: EpoolTerminalsMongo
    order_parts: list[MonopoliaOrder]
    delivery_parameters: DeliveryParameters
    # receiver_dadata: Optional[DadataCleanModel]  # https://github.com/hflabs/dadata-py
    # sender_dadata: DadataCleanModel
