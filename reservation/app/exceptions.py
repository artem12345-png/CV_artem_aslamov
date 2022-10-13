class OracleDBNotConnected(Exception):
    def __init__(self):
        super().__init__("База данных Oracle недоступна")
