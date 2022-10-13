from app.base.sms.sms_formatter import SMSFormatter
from app.base.sms.sms_sender import SMSSender
from app.base.sms.utils import get_number
from app.base.status_updater.models import StatusApplication
from app.db import DBS
from app.db.queries.mysql import QUERY_GET_IDZAKAZ_BY_IDMONOPOLIA
from app.settings.consts import TK_SMS_STATUSES
from app.settings.log import logger


async def _add_application_to_base(idmonopolia, error):
    mng = DBS["mongo_epool_admin"]["client"].get_collection("tk_sms")
    await mng.insert_one({"_id": idmonopolia, "error": error})


async def get_idzakaz(idmonopolia):
    mysql_read = DBS["mysql"]
    res = await mysql_read.fetch_one(
        QUERY_GET_IDZAKAZ_BY_IDMONOPOLIA, {"idmonopolia": idmonopolia}
    )
    return int(res[0])


class SMSHandler:
    """
    Специализируется на принятии заявки
    и передачи в случае чего на отправку
    """

    def __init__(self, idtk: int, sender: SMSSender):
        self._states = TK_SMS_STATUSES[idtk]
        self.sender = sender
        self.formatter = SMSFormatter(idtk=idtk)

    async def _is_need_send(self, application: StatusApplication) -> bool:
        """
        В каких случаях нужно отправлять:
        1) Для этого заказа не было отправок СМС,
        2) Заявка была принята транспортной компанией.
        """
        mng = DBS["mongo_epool_admin"]["client"].get_collection("tk_sms")
        resp = await mng.find_one({"_id": application.idmonopolia})
        if resp:
            return False
        elif application.status in self._states:
            return True
        else:
            return False

    async def handle(self, application: StatusApplication, test: bool = False):
        """
        Принимает решение об отправке
        """
        if test:
            return
        if await self._is_need_send(application):
            logger.info(
                f"SMS-HANDLER: отправка сообщения "
                f"по заявке idmonopolia={application.idmonopolia}"
            )
            error = False
            try:
                phone = await get_number(application.idmonopolia)
                message = self.formatter.format(
                    application.tk_num, application.idmonopolia
                )
                idzakaz = await get_idzakaz(application.idmonopolia)
                await self.sender.send(phone, message, application.idmonopolia, idzakaz)
                logger.info(
                    f"SMS-HANDLER: отправка сообщения завершена "
                    f"по заявке idmonopolia={application.idmonopolia}"
                )
            except Exception as e:
                error = True
                logger.warning(
                    f"SMS-HANDLER: не удалось отправить сообщение "
                    f"по заявке idmonopolia={application.idmonopolia}. Причина: {e}"
                )

            # Даже если нам не удалось отправить СМС, то не будем отправлять, чтобы не ввести в заблуждение
            await _add_application_to_base(application.idmonopolia, error)
