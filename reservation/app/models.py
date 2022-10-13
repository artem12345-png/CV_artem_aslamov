from pydantic import BaseModel, Field, root_validator


class CancelRequest(BaseModel):
    idzakaz: int | None
    base_id: int | None


class FakeEPLTmpZakazTovar(BaseModel):
    idzakaz: int = 1
    idgood: str = Field(
        ...,
        description="Это idgood из [ep_zakaz_parts], но он должен быть приведен к строковому"
                    " типу, т.к. в монополии это код товара и он строковый varchar2(50)",
        max_length=50,
    )
    amount: int = Field(..., description="Количество товара amount из [ep_zakaz_parts]")
    card_id: int = Field(..., description="НЕИЗВЕСТНО. Пока пустой")


class FakeEPLTmpZakaz(BaseModel):
    idzakaz: int
    note: str = Field(
        ..., description="Примечание, собирается из данных покупателя", max_length=2000
    )
    klient_id: int


class EPLTmpZakaz(BaseModel):
    idzakaz: int
    note: str = Field(
        ..., description="Примечание, собирается из данных покупателя", max_length=2000
    )
    klient_id: int

    class Good(BaseModel):
        idgood: str
        amount: int
        price: int
        card_id: int = 0

    goods: list[Good] | None


class EPLTmpZakazTovar(BaseModel):
    idzakaz: int
    idgood: str = Field(
        ...,
        description="Это idgood из [ep_zakaz_parts], но он должен быть приведен к строковому"
                    " типу, т.к. в монополии это код товара и он строковый varchar2(50)",
        max_length=50,
    )
    amount: int = Field(..., description="Количество товара amount из [ep_zakaz_parts]")
    price: int = Field(..., description="Цена товара price из [ep_zakaz_parts]")
    card_id: int = Field(..., description="НЕИЗВЕСТНО. Пока пустой")


class EPLBaseZakaz(BaseModel):
    idzakaz: int | None


class ChangeNote(CancelRequest, BaseModel):
    note: str

    @root_validator
    def check_params(cls, values):
        idzakaz, base_id = values.get('idzakaz'), values.get('base_id')
        if idzakaz is None and base_id is None:
            raise ValueError('idzakaz или base_id должны быть введены')
        return values



