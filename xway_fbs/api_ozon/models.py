from enum import Enum

from pydantic import BaseModel, Field, validator


class OzonStatuses(Enum):
    acceptance_in_progress = "acceptance_in_progress"
    awaiting_approve = "awaiting_approve"
    awaiting_packaging = "awaiting_packaging"
    awaiting_registration = "awaiting_registration"
    awaiting_deliver = "awaiting_deliver"
    arbitration = "arbitration"
    client_arbitration = "client_arbitration"
    delivering = "delivering"
    driver_pickup = "driver_pickup"
    not_accepted = "not_accepted"

    def __str__(self):
        return self.value


class OzonCancelID(Enum):
    """
    352 — товара нет в наличии;
    400 — остался только бракованный товар;
    401 — отмена из арбитража;
    402 — другая причина;
    665 — покупатель не забрал заказ;
    666 — отсутствует доставка в данный регион;
    667 — заказ утерян службой доставки.
    """

    havent_items = 352
    only_damaged = 400
    cancel_from_arbitrage = 401
    another_reason = 402
    receiver_didnt_get_item = 665
    cant_send_to_region = 666
    lost_by_tk = 667


class ActRequest(BaseModel):
    """
    Модель для создания акта
    https://docs.ozon.ru/api/seller/#operation/PostingAPI_PostingFBSActCreate
    """

    delivery_method_id: int = Field(
        ...,
        description="ID склада (брать из информации об отправлении в блоке "
        "warehouse -> marketplace_id)",
    )
    containers_count: int | None = Field(
        None,
        description="Количество грузовых мест. Используйте параметр, "
        "если вы подключены к доверительной приёмке и "
        "отгружаете заказы грузовыми местами. "
        "Если вы не подключены к доверительной приёмке, "
        "пропустите его.",
    )
    departure_date: str | None = Field(
        None,
        description="Дата отгрузки. Чтобы печать была доступна до дня отгрузки, "
        "в личном кабинете в настройках метода включите "
        "Печать актов приёма-передачи заранее.",
    )


class ActStatuses(BaseModel):
    added_to_act: list[str]
    removed_from_act: list[str]
    status: str

    @validator("status")
    def validate_status(cls, v):
        if v != "ready":
            raise ValueError("Act not ready")
        return v


class ActResponse(BaseModel):
    """Модель для ответа на запрос"""

    content: bytes
    statuses: ActStatuses
