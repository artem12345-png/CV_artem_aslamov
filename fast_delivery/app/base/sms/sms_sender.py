from app.base.sms.sender_api import Sender
from app.settings.log import logger


class SMSSender:
    """
    Специализируется на том, чтобы отправлять сообщения
    и кричать в логи о том, что что-то пошло не так.
    """

    def __init__(self, sender_api: Sender):
        self.sender_api = sender_api

    async def send(self, phone, message, idmonopolia, idzakaz):
        """Нам прилетает корректный телефон и корректное сообщение"""
        logger.info(f'Отправляется сообщение на {phone} с текстом "{message}"')
        resp = await self.sender_api.send(message, phone, idmonopolia, idzakaz)
        self._check_resp(phone, resp)
        return resp

    def _check_resp(self, phone, resp) -> bool:
        """
        Сообщает об ошибках, связанных с передачей сообщения
        """
        logger.info(f"response={resp} для телефона {phone}")
        logger.warning(f"Отсутствует проверка ответа")
        return True
