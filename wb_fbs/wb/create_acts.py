import base64
import datetime
import logging

from env import SETTINGS
from wb.consts import DIRECTORY
from wb.xway_request import xway_request, RequestType

logger = logging.getLogger(SETTINGS.SERVICE_NAME)


async def create_acts(order_ids: list[str]):
    # https://wiki.xway.ru/docs/sozdanie-postavki/
    data = {"order_id": order_ids}

    response = await xway_request(
        method=RequestType.post,
        api_method="/api/v1/orders/create-handover-sheet/",
        body=data,
    )

    if response.status_code == 200 and response.json().get("success"):
        act_id = response.json().get("response").get("handover_content_id")
        return act_id
    else:
        raise Exception(f"Не удалось создать акт")


async def get_act_by_id(act_id) -> str:
    # https://wiki.xway.ru/docs/zakrytie-postavki-i-poluchenie-shtrihk/
    request = {"handover_content_id": act_id}
    response = await xway_request(
        api_method="/api/v1/orders/get-handover-sheet/",
        method=RequestType.post,
        body=request,
        is_long_resp=True,
    )
    r_json = response.json()
    file_b64 = r_json.get("response_1") or r_json.get("response_512")
    file_bytes = base64.b64decode(file_b64)
    filename_result = (
        f"{DIRECTORY}/wb_act_{datetime.datetime.now(tz=datetime.timezone.utc)}.pdf"
    )
    with open(filename_result, "wb") as f:
        f.write(file_bytes)

    return filename_result
