#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Модели ответов сервиса. """

from typing import List
from typing import Optional

from pydantic import BaseModel, Field

from app.configs.env_conf import conf

# Включение проверки типов при присваивании
BaseModel.Config.validate_assignment = True


class TaskToken(BaseModel):
    """Модель токена задач."""

    token_id: str = Field(
        title='Токен, на получение результатов по созданию заявок.')


class OrderId(BaseModel):

    id_zakaz: int  # id заказа из таблицы заказов MySQL: ep_zakaz


class LabelsRequest(OrderId):

    id_monopolia: int


class StatusOrderRequest(OrderId):

    order_substatus: str


class LabelsDateRequest(BaseModel):

    date: str  # дд-мм-гг


class ResultResponse(BaseModel):

    result: str
    msg: Optional[str]  # Сообщение результата.


class ResultLabelsResponse(ResultResponse):

    pdf_labels_file: Optional[str]


class ResultActResponse(ResultResponse):

    pdf_act_file: Optional[str]
