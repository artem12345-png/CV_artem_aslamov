import re
from datetime import datetime
from string import punctuation as pnct

from dadata import Dadata

from app.db import DBS
from app.db.models import EpZakazMon4tkMySql, DadataCleanModel, DadataDeliveryModel
from app.settings.log import logger

punctuation = " " + pnct


async def get_terminal_address_dadata(order: EpZakazMon4tkMySql):
    return await _get_address_dadata("terminal", order)


async def get_delivery_address_dadata(order: EpZakazMon4tkMySql):
    return await _get_address_dadata("delivery", order)


async def _get_address_dadata(
    type_: str, order: EpZakazMon4tkMySql
) -> DadataCleanModel:
    tk_address = ""
    order_address_dadata = await cache_address_dadata(order.address)
    region = "" or order_address_dadata.region_with_type
    tk_address += f"{region}, " if region else ""

    city = "" or order_address_dadata.city_with_type
    city = city if city else order_address_dadata.settlement_with_type
    tk_address += f"{city}, " if city else ""

    if type_ == "terminal":
        if not city:
            order_tk_dadata = await _get_terminal_address(
                order.tk, f"{order.address}, "
            )
        else:
            order_tk_dadata = await _get_terminal_address(order.tk, tk_address)
    elif type_ == "delivery":
        order_tk_dadata = await _get_delivery_address(order.tk, tk_address)
    else:
        raise NotImplementedError()

    if order_tk_dadata.street:
        tk_address_dadata = order_tk_dadata
    else:
        tk_address_dadata = order_address_dadata

    logger.info(
        f"Адрес {type_} для заказа idmonopolia={order.idmonopolia} "
        f"tk_address.result={tk_address_dadata.result} "
        f"order.tk={order.tk} order.address={order.address}"
    )
    return tk_address_dadata


async def _get_terminal_address(order_tk_address: str, tk_address: str):
    _tk_address = re.sub(r"\[.*\]", "", order_tk_address)

    def find_(x, y):
        return x.lower().find(y) if x.lower().find(y) else None

    if terminal_idx := find_(order_tk_address, "терминал"):
        terminal_idx += len("терминал")

    if terminal_idx:
        # обрезаем адрес терминала
        _tk_address = _tk_address[terminal_idx:]
    else:
        splits = 1
        # тут нужно обрезать по 2 слову
        if _tk_address.lower().startswith("деловые линии"):
            splits = 2
        tmp = _tk_address.split(" ", splits)
        _tk_address = tmp[1] if len(tmp) == (splits + 1) else ""
    # очищаем от кодов филиалов и пунктуации вначале, чтобы не мешать dadata
    _tk_address = _tk_address.strip(punctuation)
    tk_address += _tk_address
    return await cache_address_dadata(tk_address)


async def _get_delivery_address(order_tk_address: str, tk_address: str):
    _tk_address = re.sub(r"\[.*\]", "", order_tk_address)
    tmp = _tk_address.split(" ", 1)
    _tk_address = tmp[1] if len(tmp) == 2 else ""
    # очищаем от кодов филиалов и пунктуации вначале, чтобы не мешать dadata
    _tk_address = _tk_address.strip(punctuation)
    tk_address += _tk_address
    tk_address = tk_address.strip(punctuation)
    return await cache_address_dadata(tk_address)


async def cache_address_dadata(address) -> DadataCleanModel:
    dadata_d = await cache_dadata("address", address)
    return DadataCleanModel(**dadata_d)


async def cache_delivery_dadata(kladr_id) -> DadataDeliveryModel:
    dadata_d = await cache_dadata("delivery", kladr_id)
    if dadata_d:
        return DadataDeliveryModel(**dadata_d)


async def cache_dadata(name, query):
    if not query:
        logger.info(f"Был передан пустой name={name}: query={query}")
        return {}
    db_ep = DBS["mongo_epool_admin"]["client"]

    # TODO: синхронная работа с dadata
    ddata: Dadata = DBS["dadata"]
    dadata_d = await db_ep.dadata_cache.find_one(
        {"query": query, "name": name}, {"_id": 0}
    )
    if not (dadata_d and dadata_d.get("dadata_d")):
        if name == "address":

            def dadata_f(query):
                return ddata.clean("address", query)

        elif name == "delivery":

            def dadata_f(query):
                r = ddata.find_by_id(name="delivery", query=query)
                return r[0]["data"] if r else {}

        else:
            raise NotImplementedError()
        dadata_d = dadata_f(query)
        if dadata_d:
            logger.info(f"Закэширован новый {name} dadata={dadata_d}")
            await db_ep.dadata_cache.update_one(
                {"query": query, "name": name},
                {"$set": {"dt": datetime.now(), "dadata_d": dadata_d}},
                upsert=True,
            )
        else:
            logger.warning(f"name={name} с query={dadata_d}" f" не смог определиться")
    else:
        dadata_d = dadata_d.get("dadata_d")
        logger.info(f'{name} "{query}" взят из кэша {dadata_d}')

    return dadata_d


def log_getter(info_type=None):
    # TODO: передавать idmonopolia
    def _log(f):
        async def __log(*args):
            r = await f(*args)
            logger.info(f"Информация о {info_type}: {r}")
            return r

        return __log

    return _log
