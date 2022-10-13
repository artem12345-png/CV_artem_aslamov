from datetime import datetime

from dadata import Dadata

from app.db.wrappers import MySQL, MongoDB
from app.delivery_calc import DeliveryCalcWrapper
from app.settings.log import logger

DBS = {}


async def clean_mysql_pool():
    try:
        await MySQL.clear_conn(DBS["mysql"])
        await MySQL.clear_conn(DBS["mysql_write"])
    except Exception as ex:
        logger.error(
            f"Cleaning mysql pool is not success: error={ex} time={datetime.now()}",
            exc_info=True,
        )


async def init_databases(config):
    """
    Usage example
    DBS["clickhouse"] = await ClickHouse.init_async(config["clickhouse"])
    DBS["mysql"] = await MySQL.init_async(config["mysql"])
    """
    logger.info("Подключаемся к БД")
    DBS["mysql"] = await MySQL.init_async(config["mysql"])
    DBS["mysql_write"] = await MySQL.init_async(config["mysql_write"])

    DBS["mongo_epool_admin"] = await MongoDB.init_async(
        config["mongodb"], db_name="epool_admin"
    )

    DBS["mongo_delivery_lists"] = await MongoDB.init_async(
        config["mongodb"], db_name="delivery_lists"
    )

    DBS["mongo_epool_admin_sync"] = MongoDB.init(
        config["mongodb"], db_name="epool_admin"
    )
    # TODO: синхронная работа с dadata
    DBS["dadata"] = Dadata(**config["dadata"])

    DBS["delivery_calc"] = DeliveryCalcWrapper(
        api_url=config["delivery_calc"]["prod_url"],
        test_api_url=config["delivery_calc"]["test_url"],
    )
    logger.info("Подключения к БД созданы")


async def shutdown_databases():
    """
    await ClickHouse.close_async(DBS["clickhouse"])
    await MySQL.close_async(DBS["mysql"])
    """
    await MySQL.close_async(DBS["mysql"])
    await MySQL.close_async(DBS["mysql_write"])
    await MongoDB.close_async(DBS["mongo_epool_admin"])

    # TODO: синхронная работа с dadata
    DBS["dadata"].close()

    if apis := DBS.get("cdek"):
        for shop_name in apis.keys():
            await apis[shop_name].aclose()

    if apis := DBS.get("pickpoint_api"):
        for shop_name in apis.keys():
            await apis[shop_name].aclose()
