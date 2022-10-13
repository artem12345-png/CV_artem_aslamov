# READ:
# ep_zakaz_mon4tk
# ep_zakaz_monopolia
# pr_good_sizes
# ep_goods_similar
# ep_zakaz_mon4tk_acc
#
# WRITE:
# ep_zakaz_mon4tk_acc

# Задача: https://youtrack.promsoft.ru/issue/EPOOL_TK-205

# Получение адреса, ТК, склада
QUERY_GET_MON4TK_BY_IDMONOPOLIA = (
    "SELECT * "
    "FROM mircomf4_epool.ep_zakaz_mon4tk "
    "WHERE idmonopolia=:idmonopolia LIMIT 1"
)

QUERY_GET_EP_ZAKAZ_BY_IDMONOPOLIA = (
    "SELECT * FROM mircomf4_epool.ep_zakaz WHERE idmonopolia=:idmonopolia LIMIT 1"
)

# состав заказа нужно смотреть в ep_zakaz_monopolia
QUERY_GET_ZAKAZ_MONOPOLIA_BY_IDMONOPOLIA = (
    "SELECT * FROM ep_zakaz_monopolia WHERE idmonopolia=:idmonopolia;"
)

# если его там нет, то в ep_zakaz_parts
QUERY_GET_ZAKAZ_PARTS_BY_IDMONOPOLIA = (
    "SELECT * "
    "FROM mircomf4_epool.ep_zakaz z "
    "JOIN ep_zakaz_parts p ON z.id=p.idzakaz "
    "WHERE z.idmonopolia=:idmonopolia;"
)

QUERY_GET_GOOD_INFO_WITH_SIZES_BY_IDGOOD = (
    "SELECT * "
    "FROM mircomf4_epool.pr_goods "
    "   LEFT JOIN mircomf4_epool.pr_good_sizes "
    "   ON pr_goods.id = pr_good_sizes.idgood "
    "WHERE pr_goods.id=:idgood;"
)

QUERY_GOODS_WITH_PROPERTY_ID = (
    "SELECT * "
    "FROM mircomf4_epool.ep_goods_similar "
    "WHERE iditem = :iditem AND idgood IN (:goods);"
)

QUERY_GET_NOT_FINISHED_PECOM_CARGOS = (
    "SELECT idmonopolia, tk_num "
    "FROM mircomf4_epool.ep_zakaz_mon4tk_acc "
    "WHERE idtk=3 AND (tk_status IS NULL OR NOT ("
    "tk_status LIKE 'Возвращен отправителю' OR "
    "tk_status LIKE 'Доставлен' OR "
    "tk_status LIKE 'Выдан на складе' OR "
    "tk_status LIKE 'Утилизирован' OR "
    "tk_status LIKE 'Не удалось отправить' OR "
    "tk_status LIKE 'Выдан ( мест%'));"
)

QUERY_UPDATE_CARGO_STATUS_BY_IDMONOPOLIA = (
    "UPDATE mircomf4_epool.ep_zakaz_mon4tk_acc "
    "SET tk_status=:tk_status, status_changed=:status_changed "
    "WHERE idmonopolia=:idmonopolia;"
)

# Логгировать алерты тех айдишников, которые не в этом множестве
QUERY_GET_IDZAKAZ_BY_IDMONOPOLIA = (
    "SELECT z.id AS idzakaz "
    "FROM mircomf4_epool.ep_zakaz z "
    "WHERE z.idmonopolia=:idmonopolia; "
)

QUERY_GET_SHOP_NAME_BY_IDMONOPOLIAS = """
SELECT 
    idmonopolia, 
    sender_name as shop
FROM mircomf4_epool.ep_zakaz_mon4tk 
WHERE idmonopolia=(:idmonopolias);
"""

QUERY_GET_TERMINALS_BY_CITY = f"""
    SELECT 
        address, title, map_n, map_e, idtk
    FROM
        tk_terminals
    WHERE title like :city and idtk=:idtk
    """
