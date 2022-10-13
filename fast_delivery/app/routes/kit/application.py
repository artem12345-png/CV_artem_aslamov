from io import BytesIO

from app.base.application import BaseApplication
from app.base.models.router import TKOrderParams
from app.base.pdf import modify_cargo_pdf
from app.db import DBS
from app.routes.kit.API import KITApi
from app.routes.kit.models.create_application import KITCreateApplication, KITCreateResponse
from app.settings.log import logger


class KITClassApplication(BaseApplication):
    def __init__(
        self,
        order_parameters: TKOrderParams,
        parameters: dict,
        timeout=5.0,
        test=False,
        force=False,
    ):
        super().__init__(order_parameters, parameters, timeout, test, force)
        self.api_client: KITApi = DBS["kit"]

    async def create(self) -> KITCreateResponse:
        """Создание заявки. Возвращает ответ от API"""
        model_param = KITCreateApplication(**self.tk_parameters)
        self.tk_resp = await self.api_client.create(model_param)
        return self.tk_resp

    async def get_order_num(self) -> str:
        """Взять номер заявки из транспортной компании"""
        return self.tk_resp.result.sale_number

    async def get_pdf(self, mode: str) -> BytesIO:
        """Взять PDF для заявки"""
        tk_num = await self.get_order_num()
        return await self.api_client.get_document(tk_num=tk_num, mode=mode)

    async def modify_pdf(self, mode: str, pdf_io: BytesIO, idmonopolia: int) -> BytesIO:
        if mode == "cargo":
            return modify_cargo_pdf(pdf_io, idmonopolia, font_size=20)
        return pdf_io
