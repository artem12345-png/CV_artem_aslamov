"""
Здесь тебе нужно написать логику взаимодействия с ТК.
"""
from base64 import b64decode
import httpx
from io import BytesIO
# TODO: Старайся так импорты не писать. Потому что читать очень трудно
from app.routes.kit.consts import HOST
from app.routes.kit.exceptions import KITFillerError
from app.routes.kit.models.create_application import KITCreateApplication, KITCreateResponse
from app.settings.log import logger

token = "SECRET"
headers = {
    "Authorization": f"Bearer {token}"
}
CREATE_APPLICATION_METHOD = "/1.0/order/create"
GET_STATUS_METHOD = "/1.0/order/status/get"
GET_DOCUMENTS_METHOD = "/1.0/order/document/get"


# TODO: Наполни этот класс
class KITApi:
    def __init__(self, token):
        self.token = token
        self.host = HOST

    async def create(self, application: KITCreateApplication) -> KITCreateResponse:
        # TODO: сделать обращение к АПИ и вернуть ответ
        # Воспользуйся переменными self.host и CREATE_APPLICATION_METHOD
        # Ответ сложи в созданную модель и верни согласно тайпхинту.

        d = application.dict()

        async with httpx.AsyncClient(timeout=15) as client:
            url = f"{self.host}{GET_STATUS_METHOD}"
            resp = await client.get(url=url, json=d, headers=headers)
        logger.debug(f"JDEApi GET {url}, resp={resp.content[:150]}")
        resp = resp.json()

        if resp.get("status") == 401:
            logger.error(f"Невалидный токен или отсутствует токен, {headers}")

        if tk_num := resp.get("status") != 1:
            KITFillerError(f"Заявка не создана {d}, {resp}")
        else:
            logger.error(f"Была создана заявка tknum={tk_num}")
            result = KITCreateResponse(result=resp.get("result"),
                                       status=resp.get("status"),
                                       message=resp.get("message"))
            return result

    def get_status(self, tk_num, idmonopolia) -> str:
        """Берёт статус заявки с номером tk_num"""
        d = {
            "cargo_number": f"{tk_num}"
        }

        async with httpx.AsyncClient(timeout=15) as client:
            url = f"{self.host}{GET_STATUS_METHOD}"
            resp = await client.get(url=url, json=d, headers=headers)
        logger.debug(f"JDEApi GET {url}, resp={resp.content[:150]}")
        resp = resp.json()
        code = resp.get("status").get("code")
        if code == "00":
            return code
        else:
            logger.error("Статус не 'Новый заказ'")

    async def get_document(self, tk_num: str, mode: str) -> BytesIO:
        # TODO: уточнить по поводу ссылки на обращение
        url = f"https://{self.host}/vD/docs/document?type={num}&id={tk_num}&token={self.token}"
        d = [{
                "sale_number": str(tk_num),
                "type_code": 2
            },
            {
                "sale_number": str(tk_num),
                "type_code": 4
            }]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, json=d, headers=headers)
        logger.debug(f"JDEApi GET {url}, resp={resp.content[:150]}")

        document_decoded = b64decode(resp.json()[0]["data"])
        return BytesIO(document_decoded)



