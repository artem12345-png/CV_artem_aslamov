import asyncio
from datetime import datetime, timedelta

import httpx

from api_base.api_base import ApiBase
from api_ozon.models import (
    ActRequest,
    ActStatuses,
    ActResponse,
    OzonStatuses,
    OzonCancelID,
)

OZON_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


class OzonAPI(ApiBase):
    def __init__(
        self,
        user_id: str,
        token: str,
        logger=None,
        url: str = "api-seller.ozon.ru",
        prefix="https",
    ):
        # for tests
        self.headers = {"Client-Id": user_id, "Api-Key": token, "Host": url}
        self.url = f"{prefix}://{url}"
        super().__init__(self.headers, self.url, logger)
        self.user_id = user_id
        self.token = token

    async def get_country(self, country) -> str:
        """
        Returns country ISO code
        https://docs.ozon.ru/api/seller/#operation/PostingAPI_ListCountryProductFbsPostingV2
        """
        if country == "КНР":
            return "CN"
        async with httpx.AsyncClient(headers=self.headers) as client:
            resp = await self._post(
                client,
                method="/v2/posting/fbs/product/country/list",
                body={"name_search": country},
            )
        return resp["result"][0]["country_iso_code"]

    async def get_act(self, request: ActRequest, wait_for: float = 0.5) -> ActResponse:
        async with httpx.AsyncClient(headers=self.headers) as client:
            body = request.dict(exclude_none=True)
            j_rsp = await self._post(
                client, method="/v2/posting/fbs/act/create", body=body
            )
            assert j_rsp.get("result"), "Act doesn't created"
            j_id_act = j_rsp["result"]

            for _ in range(20):
                await asyncio.sleep(wait_for)
                j_status_resp = await self._post(
                    client, method="/v2/posting/fbs/act/check-status", body=j_id_act
                )
                try:
                    statuses = ActStatuses(**j_status_resp["result"])
                    break
                except ValueError as e:
                    self._log(e, type_of_message="info")
                    continue

            await asyncio.sleep(20)
            act_resp = await self._post(
                client,
                method="/v2/posting/fbs/act/get-pdf",
                body=j_id_act,
                is_long_resp=True,
                raw=True,
            )

            return ActResponse(content=act_resp, statuses=statuses)

    async def get_info(self, posting_number: str, with_fields: dict | None = None):
        """
        Get information about `posting_number`.
        https://docs.ozon.ru/api/seller/#operation/PostingAPI_GetFbsPostingV3
        """
        if with_fields is None:
            with_fields = {
                "with": {
                    "analytics_data": False,
                    "barcodes": False,
                    "financial_data": False,
                    "translit": False,
                }
            }
        body = {"posting_number": posting_number, **with_fields}
        async with httpx.AsyncClient(headers=self.headers) as client:
            j_rsp = await self._post(client, method="/v3/posting/fbs/get", body=body)
        return j_rsp

    async def get_bulk_info(
        self, posting_numbers: list[str], with_fields: dict | None = None
    ):
        """
        NOT RECOMMENDED if len(posting_numbers) > 10.
        """
        if with_fields is None:
            with_fields = {
                "with": {
                    "analytics_data": False,
                    "barcodes": False,
                    "financial_data": False,
                    "translit": False,
                }
            }

        tasks = []
        for posting_number in posting_numbers:
            task = asyncio.create_task(self.get_info(posting_number, with_fields))
            tasks.append(task)

        result = []
        for task in tasks:
            resp = await task
            result.append(resp)

        return result

    async def get_all_info(
        self,
        date_from: datetime | str | None = None,
        date_to: datetime | str | None = None,
        filter_dict: dict | None = None,
        *,
        is_long_resp=False,
    ):
        """
        Gets information about whole postings after `date_from` to `date_to` with filter `filter_dict`.
        https://docs.ozon.ru/api/seller/#operation/PostingAPI_GetFbsPostingListV3
        Example response:
        {"result": [{order_id:...}, {}]}
        """
        if date_from is None:
            date_from = (datetime.now() - timedelta(days=30)).strftime(
                "%Y-%m-%dT00:00:00.000Z"
            )
        if date_to is None:
            date_to = datetime.now().strftime(OZON_DATE_FORMAT)
        if isinstance(date_from, datetime):
            date_from = date_from.strftime(OZON_DATE_FORMAT)
        if isinstance(date_to, datetime):
            date_to = date_to.strftime(OZON_DATE_FORMAT)
        if filter_dict is None:
            filter_dict = {}

        dates = {"since": date_from, "to": date_to}

        async with httpx.AsyncClient(headers=self.headers) as client:
            offset = 0
            limit = 1000
            result = {"result": {"has_next": False, "postings": []}}
            while True:
                res = await self._post(
                    client,
                    method="/v3/posting/fbs/list",
                    body={
                        "dir": "ASC",
                        "filter": {**dates, **filter_dict},
                        "limit": limit,
                        "offset": offset,
                        "translit": False,
                        "with": {"analytics_data": False, "financial_data": False},
                    },
                    is_long_resp=is_long_resp,
                )
                result["result"]["postings"] += res["result"]["postings"]
                offset += limit
                if not res["result"]["has_next"]:
                    break
        return result

    async def get_unfulfilled_info(
        self,
        date_day_: datetime | None = None,
        status: OzonStatuses | None = None,
        days: int | None = None,
        is_long_resp: bool = True,
    ):
        """
        Get all unfulfilled postings in `date_day` day.
        """
        if date_day_ is None:
            date_day_ = datetime.now()

        if days:
            date_day_ += timedelta(days=days)

        date_from = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        date_day_ = date_day_.replace(hour=0, minute=0, second=0)
        date_day: str = date_day_.strftime("%Y-%m-%dT%H:%M:%SZ")

        body: dict = {
            "dir": "ASC",
            "filter": {
                "cutoff_from": date_from,
                "cutoff_to": date_day,
                "status": str(status),
            },
            "limit": 1000,
            "offset": 0,
            "with": {
                "analytics_data": False,
                "barcodes": False,
                "financial_data": False,
                "translit": False,
            },
        }
        if status is None:
            del body["filter"]["status"]  # type: ignore

        async with httpx.AsyncClient(headers=self.headers) as client:
            resp = await self._post(
                client,
                method="/v3/posting/fbs/unfulfilled/list",
                body=body,
                is_long_resp=is_long_resp,
            )

        return resp

    async def get_warehouses_info(self):
        """
        https://docs.ozon.ru/api/seller/#operation/WarehouseAPI_WarehouseList
        """
        async with httpx.AsyncClient(headers=self.headers) as client:
            res = await self._post(client, method="/v1/warehouse/list", body={})
        return res

    async def ship(self, posting_number: str, ozon_info: dict) -> dict:
        """
        Changes status for posting_number
        awaiting_packaging -> awaiting_deliver
        Request example
        {
          "packages": [
            {"products": [{
                  "product_id": 185479045,
                  "quantity": 1
            }]}
          ],
          "posting_number": "89491381-0072-1",
          "with": {
            "additional_data": false
          }
        }
        https://docs.ozon.ru/api/seller/#operation/PostingAPI_GetProductExemplarStatus
        """
        request = {
            "posting_number": posting_number,
            "with": {"additional_data": False},
            "packages": [
                {
                    "products": [
                        {
                            "product_id": i["sku"],
                            "quantity": i["quantity"],
                        }
                        for i in ozon_info["result"]["products"]
                    ]
                }
            ],
        }
        async with httpx.AsyncClient(headers=self.headers) as client:
            res = await self._post(client, method="/v4/posting/fbs/ship", body=request)
        return res

    async def set_country(self, iso_code, posting_number, product_id):
        """
        Set country for item in posting number.
        https://docs.ozon.ru/api/seller/#operation/PostingAPI_SetCountryProductFbsPostingV2
        Example:
        {
          "country_iso_code": "NO",  # from get_country method
          "posting_number": "57195475-0050-3",
          "product_id": 180550365  # Ozon item number
        }
        """
        request = {
            "country_iso_code": iso_code,
            "posting_number": posting_number,
            "product_id": product_id,
        }
        async with httpx.AsyncClient(headers=self.headers) as client:
            res = await self._post(
                client, method="/v2/posting/fbs/product/country/set", body=request
            )
        return res

    async def get_label(self, client: httpx.AsyncClient, request) -> bytes:
        """
        Рекомендуем запрашивать этикетки через 45–60 секунд после сборки заказа.
        https://docs.ozon.ru/api/seller/#operation/PostingAPI_PostingFBSPackageLabel
        Request example:
        {
            "posting_number": [
                "48173252-0034-4"
            ]
        }
        """
        result = await self._post(
            client,
            method="/v2/posting/fbs/package-label",
            body=request,
            raw=True,
            is_long_resp=True,
        )
        return result

    async def get_returns(self, request) -> dict:
        """
        https://docs.ozon.ru/api/seller/#operation/ReturnsAPI_GetReturnsCompanyFBS
        """
        async with httpx.AsyncClient(headers=self.headers) as client:
            res = await self._post(
                client, method="/v2/returns/company/fbs", body=request
            )
        return res

    async def cancel_order(
        self,
        client,
        posting_number,
        cancel_reason: OzonCancelID,
        another_reason_text: str | None = None,
    ):
        request = {
            "posting_number": posting_number,
            "cancel_reason_id": cancel_reason.value,
            "cancel_reason_message": another_reason_text,
        }
        if cancel_reason.value != 402:
            del request["cancel_reason_message"]

        res = await self._post(client, method="/v2/posting/fbs/cancel", body=request)

        return res

    async def set_gtd(
        self,
        client,
        order_id,
        products_id: list | tuple,
        amounts: list | tuple,
        gtds: dict | None = None,
    ):
        """
        Установить для отправления id_gtd_absent
        https://docs.ozon.ru/api/seller/#operation/PostingAPI_SetProductExemplar
        """
        products = []
        for product_id, amount in zip(products_id, amounts):
            products.append(
                {
                    "product_id": product_id,
                    "exemplars": [
                        {"is_gtd_absent": True}
                        if gtds is None
                        else {"gtd": gtds[product_id]}
                        for _ in range(amount)
                    ],
                }
            )
        resp = await self._post(
            client,
            "/v4/fbs/posting/product/exemplar/set",
            {
                "posting_number": order_id,
                "products": products,
            },
        )
        return resp
