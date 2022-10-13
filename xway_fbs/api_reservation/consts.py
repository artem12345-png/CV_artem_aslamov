from enum import Enum

DEFAULT_NOTE = ""
MARKETPLACE_ID = 583
PREFIX = "/reservation"


class ReservationMethods(Enum):
    create = f"{PREFIX}/create"
    get_idmonopolia = f"{PREFIX}/get_idzakaz"
    cancel = f"{PREFIX}/cancel"
    change_note = f"{PREFIX}/change_note"

    def __str__(self):
        return self.value


class ReservationClientCreate(Enum):
    ozon = 2
    yandex = 3


WAREHOUSE_ID = 2230
