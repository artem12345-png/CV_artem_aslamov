import httpx
from pydantic.dataclasses import dataclass

from app.delivery_calc.models import DeliveryCalcRequest, DeliveryCalcResponse
from app.settings.log import logger


@dataclass
class DeliveryCalcAPI:
    api_url: str
    test_url: str

    async def request(self, method_type: str, method: str, test=False, **kwargs):
        base_url = self.api_url if not test else self.test_url
        # В данном сервисе таймаут на ответ от ТК 10 секунд.
        async with httpx.AsyncClient(timeout=10) as client:
            r = await getattr(client, method_type.lower())(
                f"{base_url}{method}?with_raw=1&show_exception=1", **kwargs
            )
        resp = r.json()

        logger.info(
            f"DeliveryCalcAPI test={test} method_type={method_type} method={method} status_code={r.status_code} "
            f"kwargs={kwargs} response={resp}",
        )

        if resp.get("error"):
            error = resp["error"]["exception"].get("error")
            if not error:
                error = resp["error"]["error"]
            raise AssertionError(error)
        assert r.status_code == 200, "Не удалось рассчитать стоимость доставки"

        return resp

    async def get(self, method, test=False, **kwargs):
        return await self.request("get", method, test=test, **kwargs)

    async def post(self, method, test=False, **kwargs):
        return await self.request("post", method, test=test, **kwargs)


class DeliveryCalcWrapper:
    tk_dict = {
        1: "baykal",
        2: "dl",
        3: "pek",
        4: "jde",
        5: "skif",
        6: "cdek",
    }

    def __init__(self, api_url: str, test_api_url: str):
        self._calc_api: DeliveryCalcAPI = DeliveryCalcAPI(api_url, test_api_url)

    async def calc_tk(
        self, tk_id, data: DeliveryCalcRequest, test=False
    ) -> DeliveryCalcResponse:
        tk_name = self.tk_dict[tk_id]
        method = f"/calc/{tk_name}/"
        r = await self._calc_api.post(method, json=data.dict(by_alias=True), test=test)
        return DeliveryCalcResponse(**r)
