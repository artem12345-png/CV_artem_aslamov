#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Модель запроса на создание заявки от магазина."""


from typing import List, Optional

from pydantic import BaseModel, Field

# Включение проверки типов при присваивании
BaseModel.Config.validate_assignment = True


class Order(BaseModel):
    """Модель заказа на доставку груза."""

    id: int = Field(title='idmonopolia')
    force: bool = False  # если этот параметр false -- запроса в ТК на создание заявки нет, берётся ответ из монги. Документы запрашиваются заново. Если true - запись убирается из монги, создание происходит заново.
    hardPacking: bool = False
    insurance: bool = False


class OrdersRequest(BaseModel):
    """Модель входящего запроса на сервис."""

    cargopickup: bool = False
    test: bool = Field(False, title='Режим тестирования.')
    arr: List[Order] = Field(title='Список заказов на доставку груза.')


class Data(BaseModel):
    """Модель данных заявки."""

    request_id: int = Field(title='id заявки, полученной от Л-Пост.')
    barcode: str = Field(title='Штрихкод, полученный от Л-Пост.')


class RequestData(BaseModel):
    """Модель данных о результате создания заявки."""

    id: int = Field(title='idmonopolia')
    data: Optional[Data] = Field(title='Данные о создании заявки.')
    error: Optional[str] = Field(title='Причина ошибки создания заявки.')


class DeleteOrderRequest(BaseModel):
    """Модель для удаления созданных заказов."""

    Orders: List[str]  # Список id созданных заявок для удаления в Л-Пост.


class CreateActRequest(BaseModel):
    """Модель запроса получения актов."""

    class Order(BaseModel):
        """Модель созданной заявки."""

        ID_Order: str  # Номер отправления, полученный в методе CreateOrders.

    Act: List[Order]  # Массив отправлений для создания акта.
