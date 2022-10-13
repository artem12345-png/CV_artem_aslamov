from abc import abstractmethod
from io import BytesIO
from typing import Protocol

from app.base.models.router import TKOrderParams


class ApplicationProtocol(Protocol):
    """
    интерфейс для работы с заявкой
    """

    async def create(self) -> dict:
        ...

    def load(self, dict_params: dict) -> None:
        ...

    def is_loaded(self) -> bool:
        ...

    async def get_order_num(self) -> str:
        ...

    async def get_pdf(self, mode: str) -> BytesIO:
        ...

    async def modify_pdf(self, mode: str, pdf_io: BytesIO, idmonopolia: int) -> BytesIO:
        ...


class BaseApplication(ApplicationProtocol):
    """
    класс для работы с заявкой
    """

    def __init__(
        self,
        order_parameters: TKOrderParams,
        tk_parameters: dict,
        timeout=5.0,
        test=False,
        force=False,
    ):
        self.order_parameters = order_parameters
        self.tk_parameters = tk_parameters
        self.timeout = timeout
        self.test = test
        self.force = force
        self.tk_resp = None

    def load(self, r):
        self.tk_resp = r
        return r

    def is_loaded(self) -> bool:
        return self.tk_resp is not None

    @abstractmethod
    async def create(self) -> dict:
        """Создание заявки. Возвращает ответ от API"""
        pass

    @abstractmethod
    async def get_order_num(self) -> str:
        """Взять номер заявки из транспортной компании"""
        pass

    @abstractmethod
    async def get_pdf(self, mode: str) -> BytesIO:
        """Взять PDF для заявки"""
        pass

    async def modify_pdf(self, mode: str, pdf_io: BytesIO, idmonopolia: int) -> BytesIO:
        return pdf_io
