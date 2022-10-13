from enum import Enum, auto
from typing import Optional, Union

from pydantic import BaseModel, Field


class AutoName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name


class DeliveryCalcRequest(BaseModel):
    class NeedCalc(str, AutoName):
        to_term = auto()
        to_addr = auto()
        to_both = auto()

    class Good(BaseModel):
        gid: Optional[int] = Field(
            description="Epool ID",
        )
        amount: int = Field(..., description="Количество", gt=0)
        weight: float = Field(..., description="Вес в килограммах", gt=0)
        volume: float = Field(..., description="Объём в м³", gt=0)
        length: Optional[float] = Field(description="Длинна в м.")
        width: Optional[float] = Field(description="Ширина в м.")
        height: Optional[float] = Field(description="Высота в м.")
        owersize: Optional[bool] = Field(default=False, description="Негабарит")

        class Config:
            anystr_strip_whitespace = True
            allow_mutation = False

    from_: str = Field(..., alias="from", description="Место отправки груза msk/nsk")
    to_city: Optional[str] = Field(description="Место назначения (город)")
    to_kladr: Optional[str] = Field(description="Место назначения (КЛАДР)")
    # to_fias_guid:Optional[str]=Field(description='Место назначения (фиас guid)')
    cost: float = Field(..., description="Стоимость груза в рублях")
    need_calc: NeedCalc = Field(
        default=NeedCalc.to_both,
        description="Нужен расчёт до терминала, адреса или оба",
    )
    goods: list[Good, ...] = Field(..., description="Список отправляемых товаров")

    idmon: Optional[int] = Field(description="Дополнительный параметр")

    class Config:
        use_enum_values = True
        anystr_strip_whitespace = True
        allow_mutation = False


class DeliveryCalcResponse(BaseModel):
    price: float = Field(..., description="Стоимость доставки")
    days: Union[int, str, None] = Field(description="Количество дней доставки")
    calculated: str = Field(
        ...,
        description="Какой расчёт выполнен - до терминала или до адреса",
    )
    tariff_code: Union[int, str, None] = Field(
        description="Идентификатор найденного тарифа"
    )
    raw: Optional[Union[dict, list[dict]]] = Field(description="Исходные ответы ТК")
