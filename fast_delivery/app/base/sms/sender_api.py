from typing import Protocol

import httpx

from app.settings.consts import DEBUG
from app.settings.consts import URL_SEND_TEST, URL_SEND

URL = URL_SEND_TEST if DEBUG else URL_SEND


class Sender(Protocol):
    async def send(self, message: str, receiver: str, idmonopolia: int, idzakaz: int):
        ...


class SenderAPI(Sender):
    def __init__(self, who: str = "epool"):
        self.who = who

    async def send(self, message: str, receiver: str, idmonopolia: int, idzakaz: int):
        async with httpx.AsyncClient() as client:
            request = {
                "phone": receiver,
                "sender": self.who,
                "text": message,
                "idzakaz": idzakaz,
                "idmonopolia": idmonopolia,
            }
            resp = await client.post(url=URL, json=request)
        return resp
