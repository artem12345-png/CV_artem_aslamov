import re
from typing import Optional

from pydantic import ValidationError
from pydantic.dataclasses import dataclass

from app.base.getters._cargo_getter import CargoBaseGetterModule
from app.base.getters.models import (
    CargoBaseGetter,
    MonopoliaOrder,
    DeliveryParameters,
)
from app.base.getters.models import ReceiverBaseGetter
from app.base.getters.models import SenderBaseGetter, DatabaseData
from app.base.getters.utils import (
    log_getter,
    cache_address_dadata,
    get_terminal_address_dadata,
    get_delivery_address_dadata,
)
from app.db import DBS
from app.db.models import (
    EpZakazMon4tkMySql,
    EpoolTerminalsMongo,
    EPZakazMySQL,
    DadataCleanModel,
    TerminalInfoMySql,
)
from app.db.queries.mysql import (
    QUERY_GET_MON4TK_BY_IDMONOPOLIA,
    QUERY_GET_ZAKAZ_PARTS_BY_IDMONOPOLIA,
    QUERY_GET_EP_ZAKAZ_BY_IDMONOPOLIA,
    QUERY_GET_ZAKAZ_MONOPOLIA_BY_IDMONOPOLIA,
    QUERY_GET_TERMINALS_BY_CITY,
)
from app.exceptions import (
    CityNotDefinedException,
    FillerException,
    OrderNotExistsException,
    EmptyStockAddressException,
    CountTerminalsException,
)
from app.settings import CONFIG
from app.settings.consts import (
    ALLOWED_CITIES,
    TK_ID_COLL_NAME,
    TK_ID_QUERY,
    SENDER_CONTACT,
)
from app.settings.log import logger
from app.tk_settings import TKSettings
from app.utils import get_dadata_city_name

avia_pattern = r".*((^| |\W)авиа($| |\W))|((^| |\W)авиадоставка($| |\W))|((^| |\W)авиаперевозка($| |\W)).*"
payment_pattern = (
    r".*((^| |\W)доставка за наш счет($| |\W))|((^| |\W)доставка за наш счёт($| |\W)).*"
)


def parse_fields_pattern(*args, template: str = None) -> bool:
    pattern = re.compile(template).match
    return any([bool(pattern(field)) for field in args])


def get_delivery_parameters(mon4tk) -> DeliveryParameters:
    # TODO: Здесь будем вытаскивать и всё остальное, что необходимо парсить из примечаний
    # При указании "авиа" используется авиадоставка
    # При указании "доставка за наш счёт" доставку оплачивает отправитель
    fields = mon4tk.tk.lower(), mon4tk.comment_as_site.lower()
    delivery_parameters = DeliveryParameters()

    delivery_parameters.is_avia = parse_fields_pattern(*fields, template=avia_pattern)

    # if not delivery_parameters.is_sender_pay:
    #     tk_settings: TKSettings = CONFIG["tk_config"][mon4tk.idtk]
    #     if (
    #         tk_settings.customer_pays_for_pickup
    #         == tk_settings.customer_pays_for_delivery
    #     ):
    #         delivery_parameters.is_sender_pay = (
    #             not tk_settings.customer_pays_for_delivery
    #         )

    return delivery_parameters


def _format_address_error(receiver):
    filler_msg = (
        f'Введенный адрес получателя "{receiver.dadata.source}". '
        f'Определенный адрес: "{receiver.dadata.result}". '
    )
    if receiver.tk_uuid:
        filler_msg += f'ID терминала: "{receiver.tk_uuid}" '
    return filler_msg


def _check_city_only(dadata: DadataCleanModel):
    """Проверяет как определён адрес. Если удалось определить только город - возвращает истину"""
    return (dadata.city or dadata.region) and dadata.street is None


@dataclass
class BaseGetters:
    idmonopolia: int
    idtk: int = None
    cargo_base_getter_module = CargoBaseGetterModule


    _db_data = None
    _tk_uuid_pattern = None
    _is_tk_city_need = False

    async def get_database_data(self) -> DatabaseData:
        idmonopolia = self.idmonopolia
        mysql = DBS["mysql"]
        mon4tk = await mysql.fetch_one(
            QUERY_GET_MON4TK_BY_IDMONOPOLIA, {"idmonopolia": idmonopolia}
        )
        # Добавил строчки 120-123 для того, чтобы работал тест test_city_only,
        # потому что при создании объекта класса в стрчоке 125 запускается валидация и райзиться ошибка, что нет idtk,
        # но оно объявляется idtk позже в функции base_db_data, но уже вывалилась ошибка,
        # поэтому пришлось сделать костыль
        if mon4tk:
            mon4tk = dict(mon4tk)
            if self.idtk:
                mon4tk['idtk'] = self.idtk
            mon4tk = EpZakazMon4tkMySql(**mon4tk)
        else:
            raise OrderNotExistsException(
                f"Нет заказа в таблице ep_zakaz_mon4tk с idmonopolia={idmonopolia}"
            )

        # Отправитель
        db_dl = DBS["mongo_delivery_lists"]["client"]
        logger.info(
            f"Попытка найти склад idwhs={mon4tk.idwhs} для idmonopolia={idmonopolia}"
        )
        if epool_terminal := await db_dl.epool_terminals.find_one(
            {"warehouse_num": mon4tk.idwhs}
        ):
            epool_terminal = EpoolTerminalsMongo(**epool_terminal)
        else:
            raise EmptyStockAddressException(
                f"Нет склада с warehouse.num={mon4tk.idwhs}, idmonopolia={idmonopolia}"
            )

        ep_zakaz = EPZakazMySQL(
            **dict(
                await mysql.fetch_one(
                    QUERY_GET_EP_ZAKAZ_BY_IDMONOPOLIA, {"idmonopolia": idmonopolia}
                )
            )
        )

        # Здесь указывается авиадоставка
        delivery_parameters = get_delivery_parameters(mon4tk)

        try:
            # состав заказа нужно смотреть в ep_zakaz_monpolia
            # если его там нет, то в ep_zakaz_parts
            cargos_info = [
                MonopoliaOrder(**dict(item))
                for item in await mysql.fetch_all(
                    QUERY_GET_ZAKAZ_MONOPOLIA_BY_IDMONOPOLIA,
                    {"idmonopolia": idmonopolia},
                )
            ]

            if not cargos_info:
                cargos_info = [
                    MonopoliaOrder(**dict(item))
                    for item in await mysql.fetch_all(
                        QUERY_GET_ZAKAZ_PARTS_BY_IDMONOPOLIA,
                        {"idmonopolia": idmonopolia},
                    )
                ]
        except ValidationError as e:
            logger.warning(e, stack_info=True)
            raise FillerException(
                f"Состава заказа ещё нет в нашей базе данных. Попробуйте позже. "
            ) from e

        # ПРАВИЛО
        if not cargos_info:
            raise FillerException(
                f"У заказа idmonopolia={idmonopolia} не найдены товары. "
            )

        self._db_data = DatabaseData(
            idmonopolia=idmonopolia,
            epool_terminal=epool_terminal,
            mon4tk=mon4tk,
            ep_zakaz=ep_zakaz,
            order_parts=cargos_info,
            delivery_parameters=delivery_parameters,
        )
        return self._db_data

    @log_getter("грузе")
    async def get_cargo_data(self) -> CargoBaseGetter:
        return await self._get_cargo_data()

    async def _get_cargo_data(self) -> CargoBaseGetter:
        """
        Класс модуля появился, потому что для оформления заявок в PickPoint нужно отказывать в регистрации грузов,
        для которых не задан или один из габаритов, или вес
        """
        cargo_module = self.cargo_base_getter_module(self._db_data)
        return await cargo_module.get()

    @log_getter("получателе")
    async def get_receiver_data(self) -> ReceiverBaseGetter:
        return await self._get_receiver_data()

    async def _get_receiver_data(self) -> ReceiverBaseGetter:
        db_data = self._db_data
        order, sender_filial = db_data.mon4tk, db_data.epool_terminal
        receiver = ReceiverBaseGetter()

        await self._get_receiver_address(receiver)
        receiver_dadata = receiver.dadata
        receiver.address = receiver_dadata.result

        # # 26/04/21 по согласованию с ДК, если в заявке указан адрес до города -- делаем доставку до терминала
        # Если определенный адрес вплоть до города, но не достаточно точен для
        # курьерской доставки -- автоматически доставка до терминала
        dadata_fias_min_lvl = 0 if receiver.dadata.region_type == "г" else 3

        if (not receiver.tk_uuid) and receiver.dadata.fias_level < dadata_fias_min_lvl:
            filler_msg = _format_address_error(receiver)
            filler_msg = (
                "Недостаточно точный адрес для доставки. "
                "Попробуйте добавить название города/области в строку адреса. "
                + filler_msg
            )
            raise FillerException(filler_msg.strip())

        if (
            receiver.is_delivery
            and dadata_fias_min_lvl <= receiver.dadata.fias_level < 8
        ):
            filler_msg = _format_address_error(receiver)
            logger.warning(
                "Не достаточно точен для курьерской доставки - "
                f"автоматически доставка до терминала idmonopolia={self.idmonopolia}. {filler_msg}"
            )
            receiver.is_delivery = False

        # если нет результата для доставки -- ошибка, если для ТК терминала, обрабатываем ниже
        city_name = await get_dadata_city_name(receiver_dadata, raise_exc=False)
        if city_name:  # Если город определился:
            receiver.city = city_name
        # если нет города для терминала, но есть метод поиска по координатам или tk_uuid
        elif (not receiver.is_delivery) and (
            receiver.tk_uuid or not self._is_tk_city_need
        ):
            # если для ТК терминала, но есть код доставки, все хорошо
            if not (
                receiver.tk_uuid
                and (receiver_dadata.geo_lon and receiver_dadata.geo_lat)
            ):
                raise CityNotDefinedException(
                    f"Для заказа idmonopolia={db_data.idmonopolia} не смог определиться "
                    f"адрес доставки. "
                    f"Попробуйте указать код терминала ТК в формате '[<КОД>]'. "
                    f"Распознанный адрес доставки '{receiver.address}'."
                )  # Если нет города - возвращаем ошибку
        # если нет результата для доставки -- ошибка,
        else:
            raise CityNotDefinedException(
                f"Для заказа idmonopolia={db_data.idmonopolia} не смог определиться "
                f"город доставки. "
                f"Попробуйте указать код терминала ТК в формате '[<КОД>]'. "
                f"Распознанный адрес доставки '{receiver.address}'."
            )  # Если нет города - возвращаем ошибку

        receiver_title = (
            order.receiver if order.payer_name == "Частное лицо" else order.payer_name
        )
        if not receiver_title:
            raise FillerException(
                f"Не заполнено имя получателя для idmonopolia={db_data.idmonopolia}"
            )

        receiver.title = receiver_title

        if order.receiver != "":
            receiver_person = order.receiver
        else:
            receiver_person = (
                order.payer_name if order.payer_name != "Частное лицо" else ""
            )

        receiver.passport = order.passport
        receiver.person = receiver_person
        receiver.phone = order.phone
        receiver.inn = order.inn
        receiver.email = order.email
        receiver.idbuyer = db_data.ep_zakaz.idbuyer
        return receiver

    async def _get_receiver_address(self, receiver=None):
        order = self._db_data.mon4tk
        if not receiver:
            receiver = ReceiverBaseGetter()
        # если в графе tk есть код терминала, используем его
        match = None
        if self._tk_uuid_pattern:
            logger.info(
                f'Для заказа idmonopolia={self.idmonopolia} попытка найти код терминала в адресе "{order.tk}"'
            )
            tk_pattern = re.compile(self._tk_uuid_pattern)
            match = tk_pattern.search(order.tk)

        if match:
            tk_uuid = match.group(1)
            logger.info(
                f"Для заказа idmonopolia={self.idmonopolia} найден "
                f'код терминала tk_uuid={tk_uuid} в адресе "{order.tk}"'
            )
            # Устанавливаем параметр: доставка не нужна
            receiver.is_delivery = False
            receiver.tk_uuid = tk_uuid
            receiver_dadata = await get_terminal_address_dadata(order)

        elif "терминал" in order.tk.lower():  # если в графе tk есть слово терминал, то
            # Устанавливаем параметр: доставка не нужна
            receiver.is_delivery = False
            # адрес - это все, что стоит после слово терминал
            receiver_dadata = await get_terminal_address_dadata(order)
        else:
            receiver.is_delivery = True
            # Заполняем поле адрес получателя
            # Если не терминал - адрес доставки
            receiver_dadata = await get_delivery_address_dadata(order)

            # Задача EPOOL_TK-147 - если нет точного адреса или терминала, то ищем терминал в указанном городе.
            # Если терминал один - выдаём его, иначе выдаём ошибку.
            if _check_city_only(receiver_dadata) and order.idtk != 3:  # 3 = ПЭК
                terminals = await self.get_terminals_by_city(receiver_dadata)
                t_count = len(terminals)

                if t_count == 1:
                    # доставка до двери не нужна
                    receiver.is_delivery = False
                    # адресом доставки будет адрес единственного терминала
                    order.address = terminals[0].address
                    receiver_dadata = await get_terminal_address_dadata(order)
                else:
                    raise CountTerminalsException(t_count)

            logger.info(
                f"Координаты получателя: {[receiver_dadata.geo_lon, receiver_dadata.geo_lat]}"
            )
        receiver.dadata = receiver_dadata
        return receiver

    @log_getter("отправителе")
    async def get_sender_data(self) -> SenderBaseGetter:
        return await self._get_sender_data()

    async def get_terminals_by_city(self, dadata):
        """Возвращает список терминалов для данного города"""
        idtk = self._db_data.mon4tk.idtk
        result = None
        city = dadata.city or dadata.region

        if collname := TK_ID_COLL_NAME.get(idtk):
            mongodb = DBS["mongo_delivery_lists"]["client"].get_collection(collname)
            result = [
                TerminalInfoMySql(idtk=idtk, **i)
                async for i in mongodb.find(*TK_ID_QUERY[idtk](dadata))
            ]
        if not result:
            mysql = DBS["mysql"]
            result = [
                TerminalInfoMySql(**i)
                for i in await mysql.fetch_all(
                    QUERY_GET_TERMINALS_BY_CITY, {"city": f"%{city}%", "idtk": idtk}
                )
            ]

        if all([city not in i.address for i in result]):
            for i in result:
                i.address = f"г {dadata.city}, {i.address}"
        return result

    async def _get_sender_data(self) -> SenderBaseGetter:
        db_data = self._db_data

        order, sender_filial = db_data.mon4tk, db_data.epool_terminal
        sender = SenderBaseGetter()
        sender.dadata = await cache_address_dadata(db_data.epool_terminal.address)
        sender.phone = sender_filial.warehouse_phone

        sender.address = sender.dadata.result
        sender.email = "support@promsoft.ru"
        sender.person = SENDER_CONTACT
        sender.warehouse_num = sender_filial.warehouse_num

        sender.title, sender.city = order.sender_name.split("/")

        # Разрешенные города отправки со складов.
        cities = ALLOWED_CITIES[db_data.mon4tk.idtk]
        if sender.city not in cities and cities[0] != "any":
            allowed_cities = ", ".join([f'"{c}"' for c in cities])
            raise FillerException(
                f"Заявки могут оформляться только для заказов со складами-отправителями "
                f"{allowed_cities}, "
                f'указанный склад "{sender.city}"'
            )

        db = DBS["mongo_epool_admin"]["client"]
        inn_r = await db.sender_requisites.find_one({"title": sender.title})
        if not inn_r:
            raise FillerException(f"В базе данных нет отправителя: {sender.title}")

        if inn_r:
            sender.inn = inn_r["inn"]
        return sender
