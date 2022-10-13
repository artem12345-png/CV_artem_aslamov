import aiomysql
import cx_Oracle
import uvicorn
from fastapi import FastAPI, Depends, APIRouter
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from app.environment import (
    DBOraclePool,
    DBMySQLPool,
    init_logging,
    logger,
    get_settings,
)
from app.exceptions import OracleDBNotConnected
from app.models import EPLTmpZakaz, CancelRequest, EPLBaseZakaz, ChangeNote
from app.utils import get_base_id, cleaner, fake_order, created_reserv

Settings = get_settings()
# сделать констатнту и ипортировать ее
prefix = "EPL" if Settings.TEST == 1 else "EPLP"
router = FastAPI()
base_router = APIRouter()
prefix_base = "/reservation"


@router.on_event("startup")
async def startup():
    init_logging()
    pool = DBOraclePool()
    await pool.get_pool()

    pool = DBMySQLPool()
    await pool.get_pool()


@router.on_event("shutdown")
async def shutdown():
    pool = DBOraclePool()
    await pool.close()

    pool = DBMySQLPool()
    await pool.close()


# todo: =====================================================/self_check===============================================


@router.get(path="/self_check")
async def self_check(
    connection_oracle: cx_Oracle.Connection = Depends(DBOraclePool().get_connection),
    connection_mysql: aiomysql.Connection = Depends(DBMySQLPool().get_connection),
):
    # убрать try + do ping for sql
    try:
        await connection_oracle.ping()
    except Exception as e:
        raise OracleDBNotConnected() from e
    async with connection_mysql.cursor() as con_sql:
        await con_sql.execute("select 1", None)
        await con_sql.fetchall()
    return {"message": "Ok"}


# todo: =====================================================/create==================================================


@base_router.post(path="/create")
async def create_reserve(
    request: EPLTmpZakaz,
    connection_oracle: cx_Oracle.Connection = Depends(DBOraclePool().get_connection),
    connection_mysql: aiomysql.Connection = Depends(DBMySQLPool().get_connection),
):
    logger.info(f"[{prefix}] Пришёл запрос {request.dict()}")

    try:
        async with connection_oracle.cursor() as cursor_orc:
            logger.info(
                f"Проверяем есть ли у нас уже резерв с таким idzakaz={request.idzakaz}"
            )
            resp = await get_base_id(request.idzakaz, cursor_orc, prefix)
            if resp is not None:
                # просто возвращать номер основания и логировать-сентри повторно ли его попытались зарезервировать
                logger.exception(
                    f"Резерв с таким номер заказа уже создан {resp}, idzakaz={request.idzakaz}"
                )
                return {"base_id": resp}

            if request.goods is None:
                try:
                    async with connection_mysql.cursor() as cursor_sql:
                        await cursor_sql.execute(
                            "select idzakaz, idgood, amount, price "
                            "FROM ep_zakaz_parts "
                            "where idzakaz=%s;",
                            (request.idzakaz,),
                        )
                        list_tovars = await cursor_sql.fetchall()
                    assert list_tovars
                    list_tovars = [
                        (int(tp[0]), str(tp[1]), int(tp[2]), int(tp[3]), 0)
                        for tp in list_tovars
                    ]
                    logger.info(f"Добавляем полученные товары {list_tovars}, idzakaz={request.idzakaz}")

                    resp = await created_reserv(
                        cursor_orc, prefix, request, list_tovars
                    )
                    await connection_oracle.commit()
                    logger.info(
                        f"закомитили в оракле создание резерва idzakaz={request.idzakaz}"
                    )
                    result = {"base_id": resp["base_id"]}
                    logger.info(result)
                except Exception as e:
                    logger.exception(e)
                    await connection_oracle.rollback()
                    result = {"error": f"Резерв не создан, idzakaz={request.idzakaz}"}
                    logger.info(result)
                return result
            try:
                list_tovars = [
                    (
                        int(request.idzakaz),
                        str(i.idgood),
                        int(i.amount),
                        int(i.price),
                        int(i.card_id),
                    )
                    for i in request.goods
                ]
                logger.info(
                    f"добавляем переданные товары {list_tovars}, idzakaz={request.idzakaz}"
                )
                resp = await created_reserv(cursor_orc, prefix, request, list_tovars)
                await connection_oracle.commit()
                logger.info(f"закомитили в оракле создание резерва {request.idzakaz}")
                result = {"base_id": resp["base_id"]}
                logger.info(result)
            except Exception as e:
                logger.exception(e)
                await connection_oracle.rollback()
                result = {"error": f"Резерв не создан, idzakaz={request.idzakaz}"}
                logger.info(result)
            return result
    except Exception as e:
        logger.exception(e)
        raise


# todo: ====================================================/get_idzakaz==============================================
# убрать везде внешние try


@base_router.post(path="/get_idzakaz")
async def get_idzakaz(
    request: EPLBaseZakaz,
    connection_oracle: cx_Oracle.Connection = Depends(DBOraclePool().get_connection),
):
    logger.info(prefix)
    try:
        async with connection_oracle.cursor() as cursor_orc:
            resp = await get_base_id(request.idzakaz, cursor_orc, prefix)
        return resp
    except Exception as e:
        logger.exception(e)
        raise


# todo: ===================================================/cancel=====================================================


@base_router.post(path="/cancel")
async def cancel(
    request: CancelRequest,
    connection_oracle: cx_Oracle.Connection = Depends(DBOraclePool().get_connection),
):
    logger.info(prefix)
    try:
        async with connection_oracle.cursor() as cursor_orc:
            base_id = request.base_id
            if base_id is None:
                logger.info(
                    f"номер основания отсутствует, ищем его в базе по idzakaz={request.idzakaz}"
                )
                base_id = await get_base_id(request.idzakaz, cursor_orc, prefix)
                assert base_id
                logger.info(
                    f"нашли в базе номер основания base_id={base_id}, idzakaz={request.idzakaz}"
                )
                base_id = base_id["base_id"]
            await cursor_orc.execute(
                f"BEGIN rust.{prefix}_base_unsign(:base_id); END;", base_id=int(base_id)
            )
            logger.info(f"расподписали резерв base_id={base_id}")
            await connection_oracle.commit()
            try:
                await cursor_orc.execute(
                    f"BEGIN RUST.{prefix}_BASE_CLOSE(:base_id); END;",
                    base_id=int(base_id),
                )
                logger.info(f"отменили резерв base_id={base_id}")
            except Exception as e:
                logger.error(
                    f"Возникла ошибка при закрытии резерва base_id={base_id}, idzakaz={request.idzakaz}"
                )
                return {
                    "error": f"Резерв расподписан, но не закрыт, base_id={base_id}, idzakaz={request.idzakaz}"
                }
        await connection_oracle.commit()
        return {base_id: "отменен"}
    except Exception as e:
        logger.exception(e)
        await connection_oracle.rollback()
        return {
            "error": f"Не удалось отменить резерв base_id={base_id}, idzakaz={request.idzakaz}"
        }


# todo: ===================================================/remainder===================================================


@base_router.post(path="/remainder")
async def remainder(
    id_tovars: list[int],
    connection_oracle: cx_Oracle.Connection = Depends(DBOraclePool().get_connection),
):
    logger.info(prefix)
    try:
        async with connection_oracle.cursor() as cursor_orc:
            await fake_order(cursor_orc, id_tovars, prefix)
            await cursor_orc.execute(
                f"select * from RUST.{prefix}_VW_STORE_CURRENT" " where IDZAKAZ = 1"
            )
            logger.info("Запросили остатки")
            resp = await cursor_orc.fetchall()
            result = {int(i[0]): i[1] for i in resp}

            await cleaner(cursor_orc, prefix)
        await connection_oracle.commit()
        return result
    except Exception as e:
        logger.exception(e)
        await connection_oracle.rollback()
        return {"error": f"не удалось посмотреть остатки"}


# todo: ============================================================/gtd================================================
# кэшировать гтд на месяц +-


@base_router.post(path="/gtd")
async def gtd(
    id_tovars: list[int],
    connection_oracle: cx_Oracle.Connection = Depends(DBOraclePool().get_connection),
):
    """
    id_tovars: Список id товаров
    """
    logger.info(prefix)
    logger.info(id_tovars)
    try:
        async with connection_oracle.cursor() as cursor_orc:
            await fake_order(cursor_orc, id_tovars, prefix)
            await cursor_orc.execute(
                f"select * from RUST.{prefix}_VW_GOODS_GTD" " where IDZAKAZ = 1"
            )

            logger.info("Запросили GTD")
            resp = await cursor_orc.fetchall()
            result = {int(i[0]): i[1] for i in resp}

            await cleaner(cursor_orc, prefix)

        await connection_oracle.commit()
        return result
    except Exception as e:
        logger.exception(e)
        await connection_oracle.rollback()
        return {"error": f"не удалось посмотреть GTD"}


# todo: ==================================================/change_note=================================================


@base_router.post(path="/change_note")
async def change_note(
    request: ChangeNote,
    connection_oracle: cx_Oracle.Connection = Depends(DBOraclePool().get_connection),
):
    logger.info(prefix)

    try:
        async with connection_oracle.cursor() as cursor_orc:
            base_id = (
                request.base_id
                if request.base_id
                else await get_base_id(request.idzakaz, cursor_orc, prefix)
            )
            logger.info(f"Обновляем примечание для резерва base_id={request.base_id}")
            await cursor_orc.execute(
                f"BEGIN rust.{prefix}_BASE_UPDATE_NOTE(:base_id, :note); END;",
                base_id=int(base_id),
                note=str(request.note),
            )
            logger.info(
                f"Поменяли примечание к резерву с base_id={request.base_id}, idzakaz={request.idzakaz}"
            )

        await connection_oracle.commit()
        return {
            "successful": f"примечание к резерву с base_id={request.base_id} изменено, idzakaz={request.idzakaz}"
        }
    except Exception as e:
        logger.exception(e)
        await connection_oracle.rollback()
        return {
            "error": f"не удалось поменять примечание к резерву с base_id={request.base_id},"
            f" idzakaz={request.idzakaz}"
        }


# todo: ===============================================================================================================

router.include_router(base_router, prefix=prefix_base)
app = SentryAsgiMiddleware(router)
# todo: Артем меняй порт обратно на 7567
if __name__ == "__main__":
    uvicorn.run(router, host="0.0.0.0", port=7567)
