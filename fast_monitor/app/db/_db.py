from ._wrappers import ClickHouse

DBS = {}


async def init_databases(SETTINGS, clickhouse=True):
    """
    Usage example
    DBS["clickhouse"] = await ClickHouse.init_async(config["clickhouse"])
    DBS["mysql"] = await MySQL.init_async(config["mysql"])
    """
    if clickhouse:
        ch_config = ClickHouse.read_settings_async(SETTINGS)
        DBS["clickhouse"] = await ClickHouse.init_async(ch_config)


async def shutdown_databases():
    """
    await ClickHouse.close_async(DBS["clickhouse"])
    await MySQL.close_async(DBS["mysql"])
    """
    if DBS.get('clickhouse'):
        await ClickHouse.close_async(DBS["clickhouse"])
