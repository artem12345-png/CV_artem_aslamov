"""
Здесь должна быть твоя модель для создания заявки и для ответа от АПИ ТК.
Пример модели смотри в Скиф-Карго.
"""
from datetime import date

from pydantic import Field, BaseModel


class KITCreateApplication(BaseModel):
    """
    https://tk-kit.com/developers/api-doc/1.0/order/create
    """
    class Debitor(BaseModel):
        # TODO: уточнил у поддержки значения этого поля
        #  debitor: str = Field(..., description="")
        debitor_type: int = Field(..., description="Код города откуда (1-физик, 2-ип, 3-юрик)")

    class Places(BaseModel):
        height: float = Field(..., description="Высота груза (см) позиции")
        width: float = Field(..., description="Ширина груза (см) позиции")
        length: float = Field(..., description="Длина груза (см) позиции")
        count_place: list[int] = Field(..., description="Количество мест в позиции")
        weight: list[int] = Field(..., description="Масса КГ позиции")
        volume: list[int] = Field(..., description="Объем М³ позиции")

    places: list[Places] = Field(..., default_factory=list,  description="Описание каждого груза")

    city_pickup_code: str = Field(..., description="Код города откуда")
    city_delivery_code: str = Field(..., description="Код города куда")

    customer: Debitor = Field(..., description="Заказчик")
    sender: Debitor = Field(..., description="Отправитель")
    receiver: Debitor = Field(..., description="Получатель")
    type_: int = Field(..., description="Вид перевозки (1 - Стандарт, 3 - Экспресс", alias='type')
    declared_price: int = Field(..., description="Объявленная стоимость груза (руб)")

    # Обязательно, если declared_price более 50 000 по умолчанию 0.
    confirmation_price: bool = Field(..., description="Наличие документов подтверждающих стоимость")


    # AG - заказчик
    # SE - отправитель
    # WE - получатель
    additional_payment_shipping: str = Field(..., description="Плательщик перевозки")
    additional_payment_pickup: str = Field(..., description="Плательщик забора груза")
    additional_payment_delivery: str = Field(..., description="Плательщик доставки груза")

    pick_up: int = Field(..., description="Забор груза (1-да, 0-нет)")
    pickup_date: date = Field(..., description="Дата забора")
    pickup_time_start: str = Field(..., description="Время начала забора")
    pickup_time_end: str = Field(..., description="Время окончания забора")

    deliver: int = Field(..., description="Доставка груза по городу (1-да, 0-нет)")
    delivery_date: date = Field(..., description="Дата доставки")
    delivery_time_start: str = Field(..., description="Время начала доставки")
    delivery_time_end: str = Field(..., description="Время окончания доставки")

    # если стоимость груза равна или более 10 000 руб.
    insurance: int = Field(..., description="Услуга страхования груза (1-yes, 0-no")
    # TODO: уточнил у поддержки значения этого поля
    insurance_agent_code: str = Field(..., description="Код страхового агента")
    # если стоимость груза равна или более 50 000 руб.
    have_doc: int = Field(..., description="Есть документы подтверждающие стоимость груза")


class KITCreateResponse(BaseModel):
    class Result:
        sale_number: int = Field(..., description="Номер заказа")
        cargo_number: str = Field(..., description="Номер груза")

    result: Result = Field(..., description="Результат")
    status: int = Field(..., description="Статус операции (1 успешно завершена, 0 - произошла ошибка)")
    message: str = Field(..., description="Сообщение")
