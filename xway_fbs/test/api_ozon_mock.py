import copy
from datetime import datetime

from api_base.api_base import ApiBase
from api_ozon.models import ActResponse, OzonStatuses, OzonCancelID

info_mock = {
    "result": {
        "posting_number": "89723295-0005-1",
        "order_id": 733717877,
        "order_number": "89723295-0005",
        "status": "delivering",
        "delivery_method": {
            "id": 23465287271000,
            "name": "Ozon Логистика курьеру, Реутов",
            "warehouse_id": 23465287271000,
            "warehouse": "Основной",
            "tpl_provider_id": 24,
            "tpl_provider": "Ozon Логистика",
        },
        "tracking_number": "",
        "tpl_integration_type": "ozon",
        "in_process_at": "2022-06-20T05:27:58Z",
        "shipment_date": "2022-06-22T10:00:00Z",
        "delivering_date": "2022-06-22T17:09:35Z",
        "provider_status": "",
        "delivery_price": "",
        "cancellation": {
            "cancel_reason_id": 0,
            "cancel_reason": "",
            "cancellation_type": "",
            "cancelled_after_ship": False,
            "affect_cancellation_rating": False,
            "cancellation_initiator": "",
        },
        "customer": None,
        "addressee": None,
        "products": [
            {
                "price": "2890.000000",
                "offer_id": "51462",
                "name": "Фильтр-насос Bestway 58381/58145, производительность 1.2 куб.м/ч",
                "sku": 567399696,
                "quantity": 1,
                "mandatory_mark": [],
                "dimensions": {
                    "height": "270.00",
                    "length": "270.00",
                    "weight": "2000",
                    "width": "250.00",
                },
                "currency_code": "RUB",
            }
        ],
        "barcodes": None,
        "analytics_data": None,
        "financial_data": None,
        "additional_data": [],
        "is_express": False,
        "requirements": {
            "products_requiring_gtd": [],
            "products_requiring_country": [],
            "products_requiring_mandatory_mark": [],
            "products_requiring_rnpt": [],
        },
        "product_exemplars": None,
        "courier": None,
    }
}


class MockOzonAPI(ApiBase):
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
        return "CN"

    async def get_act(self, request, wait_for: float = 0.5) -> ActResponse:
        with open("valid_pdf.pdf", "rb") as f:
            content = f.read()
        return ActResponse(
            content=content,
            statuses={
                "added_to_act": ["123"],
                "removed_from_act": ["123"],
                "status": "printed",
            },
        )

    async def get_info(self, posting_number: str, with_fields: dict | None = None):
        global info_mock
        return info_mock

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
        if filter_dict["status"] == OzonStatuses.delivering.value:
            global info_mock
            another_info_mock = copy.deepcopy(info_mock)
            another_info_mock["result"]["status"] = OzonStatuses.delivering.value
            return {"result": {"postings": [another_info_mock["result"]]}}
        else:
            return {"result": {"postings": []}}

    async def get_unfulfilled_info(
        self,
        date_day: datetime | None = None,
        status: OzonStatuses | None = None,
        days: int | None = None,
        is_long_resp: bool = True,
    ):
        global info_mock
        info_packaging = copy.deepcopy(info_mock)
        info_packaging["result"]["status"] = OzonStatuses.awaiting_packaging.value
        list_orders = [info_packaging["result"]]
        return {"result": {"postings": list_orders}}

    async def get_warehouses_info(self):
        """
        https://docs.ozon.ru/api/seller/#operation/WarehouseAPI_WarehouseList
        """
        warehouses = [
            {
                "warehouse_id": 23465287271000,
                "name": "Основной",
                "is_rfbs": False,
                "is_able_to_set_price": False,
                "has_entrusted_acceptance": False,
                "first_mile_type": {
                    "dropoff_point_id": "",
                    "dropoff_timeslot_id": 0,
                    "first_mile_is_changing": False,
                    "first_mile_type": "PickUp",
                },
                "is_kgt": False,
                "can_print_act_in_advance": False,
                "min_working_days": 5,
                "is_karantin": False,
                "has_postings_limit": False,
                "postings_limit": -1,
                "working_days": [1, 2, 3, 4, 5, 6, 7],
                "min_postings_limit": 40,
                "is_timetable_editable": True,
            },
            {
                "_id": 23623588487000,
                "warehouse_id": 23623588487000,
                "name": "КГТ",
                "is_rfbs": False,
                "is_able_to_set_price": False,
                "has_entrusted_acceptance": False,
                "first_mile_type": {
                    "dropoff_point_id": "",
                    "dropoff_timeslot_id": 0,
                    "first_mile_is_changing": False,
                    "first_mile_type": "PickUp",
                },
                "is_kgt": True,
                "can_print_act_in_advance": False,
                "min_working_days": 5,
                "is_karantin": False,
                "has_postings_limit": False,
                "postings_limit": -1,
                "working_days": [1, 2, 3, 4, 5, 6, 7],
                "min_postings_limit": 10,
                "is_timetable_editable": True,
            },
        ]
        return {"result": warehouses}

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
        _ = {
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
        return {"result": [posting_number], "additional_data": []}

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

        return {"product_id": product_id, "is_gtd_needed": True}

    async def get_label(self, client, request) -> bytes:
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
        with open("test/valid_pdf.pdf", "rb") as f:
            content = f.read()
        return content

    async def get_returns(self, request) -> dict:
        return {"result": {"returns": [{"return_date": "2022-05-20T15:15:15+00:00"}]}}

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

        return {"result": True}

    async def set_gtd(
        self, client, order_id, products_id: list | tuple, gtds: dict | None = None
    ):
        """
        Установить для отправления id_gtd_absent
        https://docs.ozon.ru/api/seller/#operation/PostingAPI_SetProductExemplar
        """

        _ = {
            "posting_number": order_id,
            "products": [
                {
                    "product_id": product_id,
                    "exemplars": [
                        {"is_gtd_absent": True}
                        if gtds is None
                        else {"gtd": gtds[product_id]}
                    ],
                }
                for product_id in products_id
            ],
        }

        return {"result": True}
