from app.env import SETTINGS


class MySQL:
    @staticmethod
    def read_settings_async(prefix="", connection_string=True):
        if prefix:
            prefix = "_" + prefix.upper()

        config = dict()
        settings = SETTINGS.dict()["MYSQL" + prefix]
        config["user"] = settings["user"]
        if password := settings["pass"]:
            config["password"] = password
        config["host"] = settings["host"]
        config["port"] = settings.get("port", 3306)
        config["db"] = settings["db"]

        connection_string = "mysql://"
        for key, value in config.items():
            if key == "user":
                connection_string += value
            elif key == "password":
                connection_string += f":{value}"
            elif key == "host":
                connection_string += f"@{value}"
            elif key == "port":
                connection_string += f":{value}"
            elif key == "db":
                connection_string += f"/{value}"
        return {"connection_string": connection_string}

    @staticmethod
    async def init_async(config):
        from databases import Database

        database = Database(
            config["connection_string"], minsize=0, maxsize=10, pool_recycle=60
        )
        await database.connect()
        # Проверка подлкючения
        assert await database.fetch_one("SELECT version()")
        return database

    @staticmethod
    async def close_async(connect):
        if connect.is_connected:
            await connect.disconnect()

    @staticmethod
    def read_settings():
        return MySQL.read_settings_async()

    @staticmethod
    async def clear_conn(connect):
        from databases.backends.mysql import MySQLBackend

        mysql_backend: MySQLBackend = connect._backend
        await mysql_backend._pool.clear()

    @staticmethod
    def init(config):
        import MySQLdb

        config["autocommit"] = True
        connection = MySQLdb.connect(**config)
        cursor = connection.cursor()

        connect = {"connection": connection, "cursor": cursor}
        return connect

    @staticmethod
    def close(connect):
        connect["cursor"].close()


class MongoDB:
    @staticmethod
    def read_settings_async(suffix=""):
        suffix = f"_{suffix.upper()}" if suffix else ""

        config = dict()
        settings = SETTINGS.dict()
        config["connection_string"] = settings[f"MONGODB_CONNECTION_STRING{suffix}"]
        return config

    @staticmethod
    async def init_async(config, db_name=None):
        import motor.motor_asyncio as aiomotor

        conn = aiomotor.AsyncIOMotorClient(config["connection_string"])
        db = conn.get_database(name=db_name)

        connect = {"client": db}
        return connect

    @staticmethod
    async def close_async(connect):
        connect["client"].client.close()

    @staticmethod
    def read_settings(suffix=""):
        return MongoDB.read_settings_async(suffix=suffix)

    @staticmethod
    def init(config, db_name=""):
        from pymongo import MongoClient

        conn = MongoClient(config["connection_string"])
        db = conn.get_database(name=db_name)
        connect = {"client": db}
        return connect
