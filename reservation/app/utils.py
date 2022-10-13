from app.environment import logger
from app.consts import dobj_id


async def get_base_id(request: int, con, prefix):
    await con.execute(
        f"select base_id, idzakaz from RUST.{prefix}_BASE_ZAKAZ where idzakaz=:var",
        var=int(request),
    )
    resp = await con.fetchall()
    logger.info(f"функция по взятию номера основания отработала успешно, ответ={resp}")
    if len(resp) == 0:
        return None
    else:
        logger.info(resp)
        resp = resp[0]
        return {"base_id": resp[0], "idzakaz": resp[1]}


async def cleaner(con, prefix, var=1):
    await con.execute(
        f"DELETE FROM RUST.{prefix}_TMP_ZAKAZ  WHERE IDZAKAZ=:var", var=int(var)
    )
    await con.execute(
        f"DELETE FROM RUST.{prefix}_TMP_ZAKAZ_TOVAR  WHERE IDZAKAZ=:var", var=int(var)
    )
    logger.info("отчистили временные таблицы")


async def fake_order(con, id_goods, prefix):
    list_tovars = [(1, str(i), 1, 1, 0) for i in id_goods]
    await con.execute(
        f"INSERT INTO RUST.{prefix}_TMP_ZAKAZ VALUES "
        "(:IDZAKAZ, :BASETP_ID, :DOBJ_ID, :NOTE, :KLIENT_ID)",
        (1, int(585), int(dobj_id), "test", 3),
    )
    logger.info("Создали ложный заказ")
    await con.executemany(
        f"INSERT INTO RUST.{prefix}_TMP_ZAKAZ_TOVAR VALUES "
        "(:IDZAKAZ, :IDGOOD, :AMOUNT, :PRICE, :CARD_ID)",
        list(list_tovars),
    )
    logger.info("Добавили товары в ложный заказ")


async def created_reserv(cursor_orc, prefix, request, list_tovars):
    basetp_id = {2: 583, 3: 585, 4: 587}[request.klient_id]
    await cursor_orc.execute(
        f"INSERT INTO RUST.{prefix}_TMP_ZAKAZ VALUES "
        "(:IDZAKAZ, :BASETP_ID, :DOBJ_ID, :NOTE, :KLIENT_ID)",
        (
            int(request.idzakaz),
            int(basetp_id),
            int(dobj_id),
            str(request.note),
            int(request.klient_id),
        ),
    )
    logger.info(
        f"INSERT INTO RUST.{prefix}_TMP_ZAKAZ VALUES "
        f"({int(request.idzakaz), int(basetp_id), int(dobj_id), str(request.note), int(request.klient_id)})"
    )

    logger.info(
        f"{request.idzakaz, basetp_id, dobj_id, request.note, request.klient_id}"
        f" добавили в базу Оракла успешно"
    )

    await cursor_orc.executemany(
        f"INSERT INTO RUST.{prefix}_TMP_ZAKAZ_TOVAR VALUES "
        "(:IDZAKAZ, :IDGOOD, :AMOUNT, :PRICE, :CARD_ID)",
        list(list_tovars),
    )
    logger.info(f"{list_tovars} добавили в базу Оракла успешно ")
    logger.info(f"begin RUST.{prefix}_NEW_BASE(:1); end;")
    await cursor_orc.execute(
        f"begin RUST.{prefix}_NEW_BASE(:1); end;", [int(request.idzakaz)]
    )
    logger.info(
        f"Процедура по созданию резерва создана успешно idzakaz={request.idzakaz}"
    )
    resp = await get_base_id(request.idzakaz, cursor_orc, prefix)

    await cleaner(cursor_orc, prefix, request.idzakaz)

    return resp
