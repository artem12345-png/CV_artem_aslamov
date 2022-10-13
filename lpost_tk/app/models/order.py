#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from typing import List
from typing import Optional

from pydantic import BaseModel, Field
from app.configs.definitions import mm, gr


# Включение проверки типов при присваивании
BaseModel.Config.validate_assignment = True


class Product(BaseModel):
    """Модель товара."""

    NameShort: str = 'Оборудование'  # Наименование товара.
    Price: float  # Цена за единицу товара.
    NDS: int = 20  # Значение НДС для товара.
    Quantity: int  # Количество единиц товара в ящике. Единица измерения – штуки.


class Cargo(BaseModel):
    """Модель ящика отправления."""

    Length: int  # Длина n-го ящика. Единица измерения - миллиметр.
    Width: int  # Ширина n-го ящика. Единица измерения - миллиметр.
    Height: int  # Высота n-го ящика. Единица измерения - миллиметр.
    Weight: int  # Масса n-го ящика. Единица измерения - грамм.
    Product: List[Product]  # Массив товаров в ящике.


class Order(BaseModel):
    """Модель отправления."""

    OrderType: int = 1  # Тип отправления. 1 – Отправление с типом «Доставить».
    PartnerNumber: str  # Номер отправления в системе партнера.
    ID_PickupPoint: Optional[int]  # Идентификатор Пункта доставки. Является обязательным для создания отправления с доставкой в ПВЗ.
    ID_Sklad: int = 3  # Идентификатор склада перевозчика.
    IssueType: int = 0  # Тип выдачи отправления. 0 - полная выдача без вскрытия, 1 – полная выдача со вскрытием, 2 - частичная выдача.
    Address: Optional[str]  # Адрес доставки (заполняется только для курьерской доставки). Адрес доставки включает в себя Населенный пункт, Улицу, Дом, Строение/Корпус.
    Flat: Optional[int]  # Квартира/офис.
    Value: float  # Объявленная стоимость отправления. Используется для расчета суммы страхового взноса.
    SumPayment: float = 0  # Сумма, которую требуется взять с получателя.
    SumPrePayment: float  # Сумма предоплаты.
    CustomerNumber: str  # Номер отправления, который известен получателю.
    isEntity: int = 0  # Тип получателя отправления: 0 – физ. лицо,1 – юр. лицо.
    CustomerName: str  # ФИО получателя или название организации.
    Phone: int  # Номер телефона для связи с получателем и SMS информирования.
    Email: Optional[str]  # E-mail получателя. При выборе типа получателя Юр.лица, параметр является обязательным.
    Cargoes: List[Cargo]  # Массив ящиков в отправлении.


class OrderList(BaseModel):
    """Модель массива отправлений."""

    Order: List[Order]


class ProductDefault(BaseModel):
    """Модель товара по умолчанию. """

    length: float = 0.1 * mm  # В мм.
    width: float = 0.1 * mm
    height: float = 0.1 * mm
    # totalVolume: float = 0.001
    totalWeight: float = 0.5 * gr  # Решение Назарова, вес в грамм.
    freightName: str = 'Оборудование'
    oversizedVolume: Optional[float]
    oversizedWeight: Optional[float]


class OrderData(BaseModel):
    """Модель данных заказа из MySQL."""

    class Good(BaseModel):
        """Модель параметров товара."""

        idgood: int
        price: float
        weight: int
        length: int
        width: int
        height: int
        amount: int

    idmonopolia: int
    goods: List[Good]
    tk: str
    sender_name: str
    idwhs: int
    payer_name: str
    comment_as_site: str
    address: str
    receiver: str
    passport: str
    inn: str
    phone: str
    email: str
