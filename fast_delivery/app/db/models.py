from typing import Optional

from pydantic import BaseModel, Field, validator, root_validator

from app.exceptions import (
    NoAddressException,
    NoTKException,
    FillerException,
    EmptyStockAddressException,
)


class EPZakazMySQL(BaseModel):
    """
    Неполная модель
    """

    idmonopolia: int
    idmarket: int
    idbuyer: int
    delivery_account: int = Field(..., description="Стоимость доставки")
    delivery_cost: Optional[int]


class PrGoodsMySql(BaseModel):
    """
    pr_goods
    """

    id: int = Field(..., description="PRIMARY KEY (`id`),")
    idcat: int = Field(..., description="KEY `idcat` (`idcat`),")
    idfirm: int = Field(..., description="KEY `idfirm` (`idfirm`),")
    artikul_firm: str
    country: str
    title: str
    unit: Optional[str]
    cost_crm: int
    price: int = 0
    price_dealer: int = Field(..., description="склад из БТ")
    price_rupool: int = Field(..., description="")
    price_nsk_shop: int = Field(..., description="цена аквамаркет")
    descr_short: str = Field(..., description="описание для списка из параметров")
    search_body: str = Field(..., description="описание для списка из параметров")
    is_img: Optional[int]
    discount_epool: str
    discount_rupool: str
    is_hit: int = Field(default=0, description="посещаемость")
    is_store: int = Field(
        default=0,
        description="3 - на складе, 2 - меньше 2 недель у поставщиков, 1 - меньше 2 месяцев",
    )
    is_sale: int = Field(
        default=0, description="распродажа. KEY `is_sale` (`is_sale`),"
    )
    idstock: int = Field(..., description="KEY `idstock` (`idstock`)")
    idstock_nsk: int
    is_free_delivery: int = Field(..., description="бесплатная доставка")
    stock_code: str = ""
    popular_sort: int
    sites: str
    country_made: str
    isactive: int = Field(default=1)
    id_gift: int


class PrGoodSizesMySql(BaseModel):
    idgood: int
    weight: float = 0.5
    volume: float = 0.1
    length: float = 0
    width: float = 0
    height: float = 0


class EpZakazMon4tkMySql(BaseModel):
    idmonopolia: int
    sender_name: Optional[str]
    payer_name: Optional[str]
    inn: Optional[str]
    passport: Optional[str]
    comment_as_site: Optional[str]
    idwhs: Optional[int]
    tk: Optional[str]
    email: Optional[str]
    address: Optional[str]
    receiver: Optional[str]
    phone: Optional[str]
    sum_from_mon: Optional[int]
    idtk: Optional[int]

    @validator("email")
    def validate_email(cls, v):
        return ""

    @validator("idtk")
    def validate_idtk(cls, v, values):
        if not v:
            raise NoTKException(idmonopolia=values['idmonopolia'])
        else:
            return v

    @root_validator()
    def validate_address(cls, values):
        if not (values['address'] or values['tk']):
            raise NoAddressException(
                f"Нет адреса в таблице ep_zakaz_mon4tk с idmonopolia={values['idmonopolia']}"
            )
        else:
            return values


class EpoolTerminalsMongo(BaseModel):
    _id: str
    title: str
    address: str
    warehouse_num: int
    warehouse_phone: str
    latitude: float
    longitude: float

    @validator("address")
    def validate_adress(cls, v, values):
        if not v:
            raise EmptyStockAddressException(
                f'Нет адреса склада города "{values["title"]}"'
            )
        else:
            return v


class TkTerminalsMySql(BaseModel):
    """
    mircomf4_epool.tk_terminals
    """

    idtk: int
    idcity: int
    title: str
    map_n: Optional[str]
    map_e: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    working_hours: Optional[str]
    is_cash_on_delivery: Optional[str]
    for_del: Optional[str]
    tk_uid: str


class DadataCleanModel(BaseModel):
    """
    https://github.com/hflabs/dadata-py
    https://dadata.ru/api/clean/address/
    """

    source: str = Field(default=None, description="Исходный адрес одной строкой")
    result: str = Field(
        default=None, description="Стандартизованный адрес одной строкой"
    )
    postal_code: str = Field(default=None, description="Индекс")
    country: str = Field(default=None, description="Страна")
    country_iso_code: str = Field(default=None, description="ISO-код страны")
    federal_district: str = Field(default=None, description="Федеральный округ")
    region_fias_id: str = Field(default=None, description="ФИАС-код региона")
    region_kladr_id: str = Field(default=None, description="КЛАДР-код региона")
    region_iso_code: str = Field(default=None, description="ISO-код региона")
    region_with_type: str = Field(default=None, description="Регион с типом")
    region_type: str = Field(default=None, description="Тип региона (сокращенный)")
    region_type_full: str = Field(default=None, description="Тип региона")
    region: str = Field(default=None, description="Регион")
    area_fias_id: str = Field(default=None, description="ФИАС-код района")
    area_kladr_id: str = Field(default=None, description="КЛАДР-код района")
    area_with_type: str = Field(default=None, description="Район в регионе с типом")
    area_type: str = Field(
        default=None, description="Тип района в регионе (сокращенный)"
    )
    area_type_full: str = Field(default=None, description="Тип района в регионе")
    area: str = Field(default=None, description="Район в регионе")
    city_fias_id: str = Field(default=None, description="ФИАС-код города")
    city_kladr_id: str = Field(default=None, description="КЛАДР-код города")
    city_with_type: str = Field(default=None, description="Город с типом")
    city_type: str = Field(default=None, description="Тип города (сокращенный)")
    city_type_full: str = Field(default=None, description="Тип города")
    city: str = Field(default=None, description="Город")
    city_area: str = Field(
        default=None, description="Административный округ (только для Москвы)"
    )
    city_district_fias_id: str = Field(
        default=None,
        description="ФИАС-код района города "
        "(заполняется, только если район есть в ФИАС)",
    )
    city_district_kladr_id: str = Field(
        default=None, description="КЛАДР-код района города (не заполняется)"
    )
    city_district_with_type: str = Field(
        default=None, description="Район города с типом"
    )
    city_district_type: str = Field(
        default=None, description="Тип района города (сокращенный)"
    )
    city_district_type_full: str = Field(default=None, description="Тип района города")
    city_district: str = Field(default=None, description="Район города")
    settlement_fias_id: str = Field(
        default=None, description="ФИАС-код населенного пункта"
    )
    settlement_kladr_id: str = Field(
        default=None, description="КЛАДР-код населенного пункта"
    )
    settlement_with_type: str = Field(
        default=None, description="Населенный пункт с типом"
    )
    settlement_type: str = Field(
        default=None, description="Тип населенного пункта (сокращенный)"
    )
    settlement_type_full: str = Field(
        default=None, description="Тип населенного пункта"
    )
    settlement: str = Field(default=None, description="Населенный пункт")
    street_fias_id: str = Field(default=None, description="ФИАС-код улицы")
    street_kladr_id: str = Field(default=None, description="КЛАДР-код улицы")
    street_with_type: str = Field(default=None, description="Улица с типом")
    street_type: str = Field(default=None, description="Тип улицы (сокращенный)")
    street_type_full: str = Field(default=None, description="Тип улицы")
    street: str = Field(default=None, description="Улица")
    house_fias_id: str = Field(default=None, description="ФИАС-код дома")
    house_kladr_id: str = Field(default=None, description="КЛАДР-код дома")
    house_type: str = Field(default=None, description="Тип дома (сокращенный)")
    house_type_full: str = Field(default=None, description="Тип дома")
    house: str = Field(default=None, description="Дом")
    block_type: str = Field(
        default=None, description="Тип корпуса/строения (сокращенный)"
    )
    block_type_full: str = Field(default=None, description="Тип корпуса/строения")
    block: str = Field(default=None, description="Корпус/строение")
    entrance: str = Field(default=None, description="Подъезд")
    floor: str = Field(default=None, description="Этаж")
    flat_fias_id: str = Field(default=None, description="ФИАС-код квартиры")
    flat_type: str = Field(default=None, description="Тип квартиры (сокращенный)")
    flat_type_full: str = Field(default=None, description="Тип квартиры")
    flat: str = Field(default=None, description="Квартира")
    flat_area: str = Field(default=None, description="Площадь квартиры")
    square_meter_price: str = Field(default=None, description="Рыночная стоимость м²")
    flat_price: str = Field(default=None, description="Рыночная стоимость квартиры")
    postal_box: str = Field(default=None, description="Абонентский ящик")

    fias_id: str = Field(
        default=None,
        description="ФИАС-код адреса (идентификатор ФИАС) "
        "HOUSE.HOUSEGUID — если дом найден в ФИАС "
        "ADDROBJ.AOGUID — в противном случае",
    )
    fias_code: str = Field(
        default=None,
        description="Иерархический код адреса в ФИАС "
        "(СС+РРР+ГГГ+ППП+СССС+УУУУ+ДДДД)",
    )
    fias_level: int = Field(
        default=1000,
        description="Уровень детализации, до которого адрес найден в ФИАС "
        "0 — страна "
        "1 — регион "
        "3 — район "
        "4 — город "
        "5 — район города "
        "6 — населенный пункт "
        "7 — улица "
        "8 — дом "
        "65 — планировочная структура "
        "90 — доп. территория "
        "91 — улица в доп. территории "
        "-1 — иностранный или пустой",
    )
    fias_actuality_state: str = Field(
        default=None,
        description=" Признак актуальности адреса в ФИАС "
        "0 — актуальный "
        "1-50 — переименован "
        "51 — переподчинен "
        "99 — удален",
    )
    kladr_id: str = Field(default=None, description="КЛАДР-код адреса")
    capital_marker: str = Field(
        default=None, description="Признак центра района или региона"
    )
    okato: str = Field(default=None, description="Код ОКАТО")
    oktmo: str = Field(default=None, description="Код ОКТМО")
    tax_office: str = Field(default=None, description="Код ИФНС для физических лиц")
    tax_office_legal: str = Field(default=None, description="Код ИФНС для организаций")
    timezone: str = Field(
        default=None,
        description="Часовой пояс города для России, "
        "часовой пояс страны — для иностранных адресов. "
        "Если у страны несколько поясов, вернёт минимальный и "
        "максимальный через слеш: UTC+5/UTC+6",
    )
    geo_lat: float = Field(default=None, description="Координаты: широта")
    geo_lon: float = Field(default=None, description="Координаты: долгота")
    beltway_hit: str = Field(default=None, description="Внутри кольцевой?")
    beltway_distance: str = Field(
        default=None, description="Расстояние от кольцевой в км."
    )
    qc_geo: int = Field(default=1000, description="Код точности координат")
    qc_complete: str = Field(default=None, description="Код пригодности к рассылке")
    qc_house: str = Field(default=None, description="Признак наличия дома в ФИАС")
    qc: str = Field(default=None, description="Код проверки адреса")
    unparsed_parts: str = Field(
        default=None, description="Нераспознанная часть адреса."
    )


class DadataDeliveryModel(BaseModel):
    class Config:
        require_by_default = False

    kladr_id: Optional[str] = Field(..., description="КЛАДР-код города")
    fias_id: Optional[str] = Field(..., description="ФИАС-код города")
    # data.boxberry_id: Optional[str]	Идентификатор города по справочнику Boxberry
    cdek_id: Optional[int] = Field(
        ..., description="Идентификатор города по справочнику СДЭК"
    )
    # data.dpd_id	Идентификатор города по справочнику DPD


class TerminalInfoMySql(BaseModel):
    """Класс для описания данных из базы tk_terminals"""

    id: int = None
    idtk: int
    idcity: int = None
    title: str
    map_n: float = None
    map_e: float = None
    address: str
    phone: str = None
    email: str = None
    working_hours: str = None
    is_cash_on_delivery: bool = None
    for_del: str = None
    tk_uid: str = None
    max_weight: float = None
    max_volume: float = None
    max_weight_per_place: float = None
    max_dimension: float = None
