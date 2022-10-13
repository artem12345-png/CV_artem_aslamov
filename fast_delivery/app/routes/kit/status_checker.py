from app.base.status_updater import TKStatusApplicationsIterator, StatusApplication
from app.db import DBS
from app.routes.kit.consts import STATUS_DESC
from app.settings.log import logger
from app.routes.kit.exceptions import KITStatusException


class KITIterator(TKStatusApplicationsIterator):
    async def get_applications_status(
        self, applications: list[StatusApplication]
    ) -> list[StatusApplication]:
        id_to_application = {i.idmonopolia: i for i in applications}

        client = DBS["kit"]
        res = []
        for idmonopolia in id_to_application.keys():
            tk_num = id_to_application[idmonopolia].tk_num
            try:
                j_resp = await client.get_status(
                    tk_num, idmonopolia=idmonopolia
                )
                if j_resp.get("status"):
                    status = STATUS_DESC[j_resp["status"]]
                else:
                    status = STATUS_DESC["Deleted"]
            except KITStatusException as e:
                logger.error(
                    f"Для заказа idmonopolia={idmonopolia} не удалось обновить статус. Ошибка ЖелДорЭкспедиции: {e}",
                    exc_info=True,
                )
                status = "Не удалось определить статус"

            res += [
                StatusApplication(idmonopolia=idmonopolia, tk_num=tk_num, status=status)
            ]

        return res
