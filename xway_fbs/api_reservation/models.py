from pydantic import BaseModel

from api_reservation.consts import DEFAULT_NOTE, MARKETPLACE_ID, WAREHOUSE_ID


class Good(BaseModel):
    idgood: str
    amount: int
    price: int
    card_id: int | None


class CreateReserve(BaseModel):
    idzakaz: int
    basetp_id: int = MARKETPLACE_ID
    dobj_id: int = WAREHOUSE_ID
    note: str = DEFAULT_NOTE
    klient_id: int
    goods: list[Good] | None = None


class ClearReserve(BaseModel):
    idzakaz: int | None
    base_id: int | None


class GetIdmonopolia(BaseModel):
    idzakaz: int


class ChangeNoteRequest(BaseModel):
    idzakaz: int | None
    base_id: int | None
    note: str
