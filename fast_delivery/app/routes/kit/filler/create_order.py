import datetime

from app.base.filler import BaseFiller
from app.exceptions import FillerException
from app.routes.kit.models import KITCreateApplication
from app.settings import CONFIG
from app.settings.log import logger
from app.tk_settings import TKSettings
from app.routes.kit.consts import (
    MANAGER,
    cashless,
    cash,
    receiver,
    count_units,
    sender,
    GTD_GUIDS,
    PAYERS_NAME,
)
from app.routes.kit.exceptions import KITFillerError
import re


class FillKITApplication(BaseFiller):
    async def fill(self, cargo_pickup: bool = True) -> KITCreateApplication:
        delivery_params = self._db_data.delivery_parameters
        if delivery_params.is_avia:
            raise FillerException("Авиадоставка для выбранной ТК не реализована.")

        tk_settings: TKSettings = CONFIG["tk_config"][self._db_data.mon4tk.idtk]

        sen = self.base_sender  # информация по отправителю из базы
        rec = self.base_receiver  # информация по получателю из базы
        # Является ли ИП
        is_sp = "ИП" in rec.person or "ИП" in rec.title
        # Является ли юрлицом
        is_entity = (
                            '"' in rec.person
                            or "ооо" in rec.person.lower()
                            or "'" in rec.person
                            or '"' in rec.title
                            or "ооо" in rec.title.lower()
                            or "'" in rec.title
        )

        legal_form = 3 if is_entity else 1
        legal_form = 3 if is_sp else legal_form

        receiver_payer, sender_payer = "AG", "SE"

        # TODO: Заполни заявку
        result = KITCreateApplication(
                city_pickup_code=sen.dadata.city_kladr_id,
                city_delivery_code=rec.dadata.city_kladr_id,
                customer=KITCreateApplication.Debitor(),
                sender=KITCreateApplication.Debitor(debitor_type=3),
                receiver=KITCreateApplication.Debitor(debitor_type=legal_form),
                type="",
                declared_price=self.base_cargo.sum_price,
                confirmation_price="",
                places=[{"height":item.height,
                         "width":item.width,
                         "length":item.length,
                         "count_place": 1,
                         "weight": item.weight,
                         "volume": item.volume}
                        for item in self.base_cargo.cargos],
                additional_payment_shipping=(receiver_payer if tk_settings.customer_pays_for_pickup else sender_payer),
                additional_payment_pickup=(receiver_payer if tk_settings.customer_pays_for_pickup else sender_payer),
                additional_payment_delivery=(receiver_payer if tk_settings.customer_pays_for_pickup else sender_payer),
                pick_up=1,
                pickup_date=datetime.datetime.today().date().isoformat(),
                pickup_time_start="10:00",
                pickup_time_end="12:00",
                deliver=rec.is_delivery,
                #delivery_date=,
                #delivery_time_start=,
                #delivery_time_end=,
                insurance=int(self.order_params.insurance),
                #insurance_agent_code=self.,
                have_doc=""
        )

        return result
