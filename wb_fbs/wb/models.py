import re

from pydantic import BaseModel, Field, validator


class Item(BaseModel):
    sku_code: str = Field(..., description="Код товара в системе Селлера")
    offer_id: str = Field(description="Код в нашей системе (idgood)")
    item_offer: int
    product_unit_price_amount: str | None = Field(
        None, description="Цена, по которой товар был продан"
    )
    amount: str | None = Field(None, description="Общая стоимость")
    lot_num: int | None = Field(
        None,
        description="Количество единиц товара в наборе"
        " (для товаров, которые продаются по несколько штук в наборе,"
        " например: елочные игрушки — 6 шаров в наборе",
    )
    adjust_amount: str | None = Field(None, description="Итоговая сумма")
    product_count: int | None = Field(None, description="Количество товара")
    logistics_service_name: str | None = Field(
        None, description="Наименование логистической службы"
    )
    logistics_amount: str | None = Field(None, description="Стоимость доставки")
    escrow_fee_rate: str | None = Field(None, description="Комиссия доставки")
    name: str | None = Field(None, description="Наименование товара")


class BasicModel(BaseModel):
    order_id: str = Field(..., description="Номер заказа в системе маркетплейса")
    order_status: str | None = Field(
        None, description="Статус заказа в системе маркетплейса"
    )
    xway_status: str | None = None
    buyer_login_id: str | None = Field(None, description="Id покупателя на Ozon")
    detail_address: str | None = Field(None, description="Подробный адрес")
    street: str | None = Field(None, description="Улица")
    city: str | None = Field(None, description="Город")
    zip: str | None = Field(None, description="Индекс")
    country: str | None = Field(None, description="Страна")
    province: str | None = Field(None, description="Регион/область")
    phone_country: str | None = Field(None, description="Телефонный код страны")
    mobile_no: str | None = Field(None, description="Номер телефона")
    pay_amount: str | None = Field(None, description="Сумма оплаты")
    symbol: str | None = Field(None, description="Наименование валюты")
    currency_code: str | None = Field(None, description="Код валюты")
    marketplace_id: int | None = Field(None, description="Id маркетплейса")
    buyer_name: str | None = Field(None, description="Имя покупателя")
    order_items: list[Item] = Field(
        [], description="Массив, содержащий информацию о товарах в заказе"
    )


class Equip(BaseModel):
    class EquipItem(BaseModel):
        quantity: str | None = Field(None, description="Количество единиц товара")
        sku: int | None = Field(
            None, description="Идентификатор предложения в системе коннектора"
        )

    posting_number: str | None = Field(
        None, description="Номер заказа в системе маркетплейса (order_id)"
    )
    weight: int | None = Field(None, description="Вес заказа в граммах")
    width: int | None = Field(None, description="Ширина упаковки заказа в см")
    height: int | None = Field(None, description="Высота упаковки заказа в см")
    depth: int | None = Field(None, description="Глубина упаковки заказа в см")
    items: list[EquipItem] = Field(None, description="Массив с предложениями")


class FullInfo(BaseModel):
    class InfoItem(BaseModel):
        id: int
        offer_id: str = Field(description="Код в нашей системе (idgood)")

        products: list
        barcode: str
        name: str
        product_id: str
        product_count: int
        discount_detail: list
        created: str
        modified: str
        afflicate_fee_rate: str
        can_submit_issue: bool
        child_id: int
        delivery_time: str
        escrow_fee_rate: str
        freight_commit_day: str
        goods_prepare_time: int
        issue_status: str
        logistics_amount: str
        logistics_service_name: str
        logistics_type: str
        money_back3x: bool
        product_snap_url: str
        product_unit: str
        product_unit_price_amount: str
        send_goods_operator: str
        show_status: str
        son_order_status: str
        total_product_amount: str
        sku_code: str
        confirmed: int
        order: int
        item_offer: int
        logistics_currency: int
        product_unit_price_currency: int
        total_product_currency: int
        id: int

    xway_status: str | None = None
    order_items: list[InfoItem]
    shop_id: int | None = None
    discount: int | None = None
    created: str | None = None
    modified: str | None = None
    order_id: str | None = None
    order_status: str | None = None
    frozen_status: str | None = None
    issue_status: str | None = None
    logistics_escrow_fee_rate: str | None = None
    fund_status: str | None = None
    gmt_pay_time: str | None = None
    has_request_loan: bool | None = None
    pay_amount: str | None = None
    buyer_login_id: str | None = None
    gmt_create: str | None = None
    gmt_update: str | None = None
    sender_status: str | None = None
    receipts: list | None = None
    shop: int | None = None
    marketplace: int | None = None
    pay_currency: int | None = None
    shipment_date: str
    item_offer: list[int]


class DateRequest(BaseModel):
    date: str

    @validator("date")
    def check_re(cls, v):
        assert re.match(
            r"^\d\d-\d\d-\d\d\d\d$", v
        ), "Формат даты должен быть dd-mm-yyyy"
        assert (
            int(v.split("-")[1]) <= 12
        ), "Месяц должен быть меньше 12 (ФОРМАТ dd-mm-yyyy)"
        return v


class Goods(BaseModel):
    class Good(BaseModel):
        idgood: int
        amount: int
        name: str

    items: list[Good]


class ChangeStatusRequest(BaseModel):
    idmonopolia: int
    id_zakaz: int
    force_label: bool = False
