class ClickHouse:
    @staticmethod
    def read_settings_async(SETTINGS):
        config = dict()
        config["url"] = SETTINGS.CH_HOST
        config["user"] = SETTINGS.CH_USER
        config["password"] = SETTINGS.CH_PASSWORD
        config["database"] = SETTINGS.CH_DATABASE
        return config

    @staticmethod
    async def init_async(config):
        from aiochclient import ChClient as Client
        from aiohttp import ClientSession

        session = ClientSession()
        client = Client(session, **config)
        assert await client.is_alive()

        connect = {
            "client": client,
            "session": session
        }
        return connect

    @staticmethod
    async def close_async(connect):
        if not connect["session"].closed:
            await connect["session"].close()
