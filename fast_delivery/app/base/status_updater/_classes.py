import asyncio
from abc import abstractmethod
from datetime import datetime

from app.base.status_updater.models import StatusApplication
from app.db import DBS
from app.db.queries.mysql import QUERY_UPDATE_CARGO_STATUS_BY_IDMONOPOLIA
from app.routes.pecom.utils import batch
from app.settings.consts import TK_ID_DICT
from app.settings.log import logger


class TKStatusApplicationsIterator:
    batch_size: int = 1
    semaphore_size: int = 1

    def __init__(self, applications: list[StatusApplication], test=False):
        self.applications = applications
        self.batch_size = self.batch_size
        self.semaphore = asyncio.Semaphore(self.semaphore_size)
        batcher = batch(self.batch_size)
        self.applications_batched = [b for b in batcher(self.applications)]
        self.test = test

    async def __aiter__(self):
        # нам возвращается в цикле корутины, результаты которых list
        # а мы хотим написать итератор, поэтому делаем yield от результата
        for st_a in await asyncio.gather(
            *[
                self.get_applications_status_filtered(apl)
                for apl in self.applications_batched
            ]
        ):
            # logger.info(f'заявки, у которых мзменился статус: {st_a}')
            if st_a:
                for a in st_a:
                    yield a

    async def get_applications_status_filtered(
        self, applications: list[StatusApplication]
    ):
        """
        возвращаем только те заявки, статус которых изменился
        """
        async with self.semaphore:
            sorted_appl = sorted(applications, key=lambda x: x.idmonopolia)
            newer_statuses = await self.get_applications_status(sorted_appl)
            # для прода
            predicate = lambda x, y: x != y

            # для теста
            if self.test:
                predicate = lambda x, y: True

            l = list(
                filter(
                    lambda z: predicate(z[0].status, z[1].status),
                    zip(sorted_appl, newer_statuses),
                )
            )
            return [t[1] for t in l]

    @abstractmethod
    async def get_applications_status(
        self, applications: list[StatusApplication]
    ) -> list[StatusApplication]:
        """
        Обрабатывает заявки из массива applications и отдает по ним статус
        Размер массива applications равен batch_size.

        Таким образом, если статус может быть только по одной заявке, считаем что в массиве applications
        находится только 1 элемент
        """
        pass


class TKStatusDB:
    def __init__(self, idtk: int, finished_statuses: list[str]):
        self.idtk = idtk
        self.finished_statuses = finished_statuses
        if not self.finished_statuses:
            raise NotImplementedError("Не может не быть финальных статусов грузов")
        mng_ep = DBS["mongo_epool_admin"]["client"]
        self.mysql_write = DBS["mysql_write"]
        self.mysql_read = DBS["mysql"]
        self.orders_coll = mng_ep.get_collection("tk_" + TK_ID_DICT[self.idtk])

    async def update_status(self, application: StatusApplication) -> None:
        mysql_write = DBS["mysql_write"]
        status_info = {"status": application.status}
        # if application.status.id:
        #     status_info["status_id"] = application.status.id

        self.orders_coll.update_one(
            {"_id": application.idmonopolia}, {"$set": status_info}
        )
        dt = datetime.now()
        await mysql_write.fetch_one(
            QUERY_UPDATE_CARGO_STATUS_BY_IDMONOPOLIA,
            {
                "idmonopolia": application.idmonopolia,
                "tk_status": application.status,
                "status_changed": dt,
            },
        )
        logger.info(
            f"{TK_ID_DICT[self.idtk].upper()} STATUS UPDATER: "
            f"груз с idmonopolia=%s обновлен %s со status=%s",
            application.idmonopolia,
            dt,
            application.status,
        )

    def get_applications_query(self):
        finish_cond = []
        for finish_st in self.finished_statuses:
            finish_cond += [f"tk_status LIKE '{finish_st}'"]
        finish_cond = " OR ".join(finish_cond)

        return (
            "SELECT idmonopolia, tk_num, tk_status AS status "
            "FROM mircomf4_epool.ep_zakaz_mon4tk_acc "
            f"WHERE idtk={self.idtk} AND (tk_status IS NULL OR "
            f"NOT ({finish_cond}));"
        )

    async def get_applications(self) -> list[StatusApplication]:
        applications = [
            dict(t)
            for t in await self.mysql_read.fetch_all(self.get_applications_query())
        ]
        # logger.info(applications[0])
        applications = [StatusApplication(**t) for t in applications]

        logger.info(
            f"{TK_ID_DICT[self.idtk].upper()} STATUS UPDATER: "
            f"количество заявок для обработки len(applications)={len(applications)}"
        )
        return applications
