from .models import DatabaseData, CargoBaseGetter, CargoQueryRes, CargoBaseItemGetter
from ...db import DBS
from ...db.queries.mysql import (
    QUERY_GET_GOOD_INFO_WITH_SIZES_BY_IDGOOD,
    QUERY_GOODS_WITH_PROPERTY_ID,
)
from ...exceptions import FillerException
from ...settings.log import logger


class CargoBaseGetterModule:
    class ValidationError(Exception):
        pass

    def __init__(self, db_data: DatabaseData):
        self.db_data: DatabaseData = db_data
        self.cargo_getter = CargoBaseGetter()

    async def get(self):
        db_data = self.db_data
        idmonopolia = db_data.idmonopolia

        cargo_getter = self.cargo_getter
        cargos = cargo_getter.cargos

        for monopolia_order in self.db_data.order_parts:
            good_info = await self._get_good_info(monopolia_order)
            _cargo = await self._create_base_item(good_info, monopolia_order)

            logger.info(
                f"Обработан товар idgood={monopolia_order.idgood} для idmonopolia={idmonopolia} с параметрами: {_cargo}"
            )
            cargos.append(_cargo)

        await self._get_cargo_properties()
        await self._create_general_properties()
        return cargo_getter

    async def _get_good_info(self, monopolia_order):
        mysql = DBS["mysql"]
        idmonopolia = self.db_data.idmonopolia
        if good_info_ := dict(
            await mysql.fetch_one(
                QUERY_GET_GOOD_INFO_WITH_SIZES_BY_IDGOOD,
                {"idgood": monopolia_order.idgood},
            )
        ):
            logger.debug(
                "Обрабатывается товар idgood=%s info=%s",
                monopolia_order.idgood,
                good_info_,
            )
            try:
                await self._validate_cargo(good_info_)
            except self.ValidationError as e:
                raise FillerException(
                    f"Товар с idgood={monopolia_order.idgood} не может быть оформлен по причине: {e}"
                )

            good_info_model = CargoQueryRes(
                **{k: v for k, v in good_info_.items() if v is not None}
            )
            logger.info(
                f"Товар для idmonopolia={idmonopolia} с параметрами: {good_info_model}"
            )
        else:
            logger.error(
                f"Товар с id={monopolia_order.idgood} не найден в таблице товаров; "
                f"idmonopolia={idmonopolia}; EPZakazMonopoliaMySql={monopolia_order}",
                exc_info=True,
            )
            raise FillerException(
                f"Товар с id={monopolia_order.idgood} не найден в таблице товаров."
            )
        return good_info_model

    async def _validate_cargo(self, good_info: dict):
        """
        выплевывет  self.ValidationError если что-то пошло не так
        """
        pass

    async def _create_base_item(self, good_info, monopolia_order):
        _cargo = CargoBaseItemGetter(
            idgood=monopolia_order.idgood,
            title=good_info.title.strip(),
            price=good_info.price,
        )
        _cargo.quantity = monopolia_order.amount
        _cargo.length = max(0.01, good_info.length)
        _cargo.height = max(0.01, good_info.height)
        _cargo.width = max(0.01, good_info.width)
        _cargo.weight = max(0.1, good_info.weight)
        _cargo.volume = max(0.01, good_info.volume)
        return _cargo

    async def _get_cargo_properties(self):
        mysql = DBS["mysql"]
        cargo_getter = self.cargo_getter

        for (service, code) in [
            # название как в pydantic модели
            ("oversized", 1),
            ("fragile", 3),
            ("warm_car", 4),
        ]:

            goods = ", ".join([str(item.idgood) for item in cargo_getter.cargos])
            if goods:
                if await mysql.fetch_all(
                    QUERY_GOODS_WITH_PROPERTY_ID, {"iditem": code, "goods": goods}
                ):
                    setattr(cargo_getter, service, True)

        # EPOOL_TK-155; нужно смотреть комментарии к основанию.
        # Если там есть слова "обрешетка" или "хрупкий груз", выставлять флаги даже если товар не хрупкий
        if any(
            x in self.db_data.mon4tk.comment_as_site
            for x in ["обрешетка", "хрупкий груз"]
        ):
            cargo_getter.fragile = True

    async def _create_general_properties(self):
        cargo_getter = self.cargo_getter

        operator_with_key = lambda f, key, **kwargs: f(
            [getattr(_cargo, key) for _cargo in cargo_getter.cargos], **kwargs
        )
        sum_with_key = lambda key: operator_with_key(sum, key)
        max_with_key = lambda key, **kwargs: operator_with_key(max, key, **kwargs)

        if sum_weight := sum_with_key("weight"):
            cargo_getter.sum_weight = sum_weight
        cargo_getter.sum_volume = sum_with_key("volume")
        # с учетом скидок и тп
        cargo_getter.sum_price = self.db_data.mon4tk.sum_from_mon
        cargo_getter.max_width = max_with_key("width", default=None)
        cargo_getter.max_length = max_with_key("length", default=None)
        cargo_getter.max_height = max_with_key("height", default=None)
