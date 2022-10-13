import datetime
from typing import Type

from app.base.sms.sender_api import SenderAPI
from app.base.sms.sms_handler import SMSHandler
from app.base.sms.sms_sender import SMSSender
from ._classes import TKStatusApplicationsIterator, TKStatusDB
from ._consts import STATUS_TIME_FROM, STATUS_TIME_TO
from ...env import SETTINGS
from ...settings.consts import TK_ID_DICT, SMS_SENDER
from ...settings.log import logger


class TKStatusUpdater:
    def __init__(
        self,
        idtk: int,
        finished_statuses: list[str],
        status_iterator_class: Type[TKStatusApplicationsIterator],
        status_db_class: Type[TKStatusDB] = TKStatusDB,
    ):
        self.idtk = idtk
        self.finished_statuses = finished_statuses
        self.status_iterator_class = status_iterator_class
        self.status_db_class = status_db_class
        self.sms_handler = SMSHandler(
            idtk=idtk, sender=SMSSender(SenderAPI(who=SMS_SENDER))
        )

    async def update_all(self, test=False):
        if not SETTINGS.STATUS_OFF:
            now_hour = datetime.datetime.now().hour
            # Время Московское (установлено в докере)
            # Вежливая отправка
            if STATUS_TIME_FROM <= now_hour < STATUS_TIME_TO:
                status_db = self.status_db_class(self.idtk, self.finished_statuses)
                applications = await status_db.get_applications()

                # для теста обрежем чутка
                if test:
                    applications = applications[:5]

                async_gen = self.status_iterator_class(applications, test=test)
                cnt = 0
                async for appl in async_gen:
                    cnt += async_gen.batch_size
                    if not test:
                        await status_db.update_status(appl)
                        await self.sms_handler.handle(appl)

                if not test:
                    logger.info(
                        f"Статус обновлен у {cnt} {TK_ID_DICT[self.idtk].upper()} заявок"
                    )
