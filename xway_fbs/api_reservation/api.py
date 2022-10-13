import httpx
from pydantic import BaseModel

from api_base.api_base import ApiBase
from api_reservation.consts import ReservationMethods, ReservationClientCreate
from api_reservation.models import (
    CreateReserve,
    ClearReserve,
    GetIdmonopolia,
    Good,
    ChangeNoteRequest,
)


class ReservationClient(ApiBase):
    def __init__(self, token, url, logger=None):
        self.headers = {"Authorization": token}
        super().__init__(self.headers, url, logger)
        self.url = url
        self.logger = logger

    async def create_reserve(
        self,
        client: httpx.AsyncClient,
        id_zakaz: int,
        client_id: ReservationClientCreate,
        note: str,
        goods: list[Good] | None = None,
    ) -> int:
        query = CreateReserve(
            idzakaz=id_zakaz, klient_id=client_id.value, note=note, goods=goods
        )
        method = ReservationMethods.create
        response = await self._post_errors(client, id_zakaz, method, query)

        return int(response["base_id"])

    async def clear_reserve(
        self,
        client: httpx.AsyncClient,
        *,
        id_zakaz: int | None = None,
        idmonopolia: int | None = None,
    ) -> None:
        query = ClearReserve(idzakaz=id_zakaz, base_id=idmonopolia)
        method = ReservationMethods.cancel
        _ = await self._post_errors(client, id_zakaz, method, query)

    async def get_idmonopolia(self, client: httpx.AsyncClient, id_zakaz: int) -> int:
        query = GetIdmonopolia(idzakaz=id_zakaz)
        method = ReservationMethods.get_idmonopolia
        response = await self._post_errors(client, id_zakaz, method, query)

        return int(response["base_id"])

    async def get_gtd(self, client: httpx.AsyncClient, idgoods: list[int]):
        resp = await self._post(
            client, "/reservation/gtd", body=idgoods, exclude_none=False
        )
        assert resp.get("error") is None, f"Не удалось взять GTD для {idgoods}"
        return resp

    async def _post_errors(
        self,
        client: httpx.AsyncClient,
        id_zakaz: int | None,
        method: ReservationMethods,
        query: BaseModel,
    ) -> dict:
        response = await self._post(
            client, method=str(method), body=query.dict(exclude_none=True)
        )
        error = response.get("error")
        assert error is None, f"{method} для {id_zakaz} завершилось с ошибкой {error}"
        return response

    async def change_note(
        self,
        client: httpx.AsyncClient,
        note: str,
        id_zakaz: int | None = None,
        base_id: int | None = None,
    ):
        query = ChangeNoteRequest(base_id=base_id, idzakaz=id_zakaz, note=note)
        resp = await self._post_errors(
            client, id_zakaz, ReservationMethods.change_note, query
        )
        return resp
