import httpx

from api_base.api_base import ApiBase
from api_reservation.consts import ReservationMethods, ReservationClientCreate
from api_reservation.models import CreateReserve, ClearReserve, GetIdmonopolia


class MockReservationClient(ApiBase):
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
        goods=None,
    ) -> int:
        _ = CreateReserve(idzakaz=id_zakaz, klient_id=client_id.value, note=note)
        _ = ReservationMethods.create

        return 1234567

    async def clear_reserve(self, client: httpx.AsyncClient, id_zakaz: int) -> None:
        _ = ClearReserve(idzakaz=id_zakaz)
        _ = ReservationMethods.cancel

    async def get_idmonopolia(self, client: httpx.AsyncClient, id_zakaz: int) -> int:
        _ = GetIdmonopolia(idzakaz=id_zakaz)
        _ = ReservationMethods.get_idmonopolia

        return 1234567
