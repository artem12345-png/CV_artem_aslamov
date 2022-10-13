from pydantic import BaseModel, validator
from app.settings.consts import TK_ID_NAME


class TKSettings(BaseModel):
    idtk: int
    customer_pays_for_pickup: bool = True
    customer_pays_for_delivery: bool = True


def settings_factory(idtk):
    return TKSettings(idtk=idtk)


TK_SETTINGS = {k: TKSettings(idtk=k) for k in TK_ID_NAME.keys()}


def get_all_settings(resp) -> dict[TKSettings]:
    global TK_SETTINGS
    temp_settings = TK_SETTINGS
    if resp is None:
        return temp_settings
    else:
        for tk_set in resp:
            TK_SETTINGS[tk_set["_id"]] = TKSettings(**{'idtk': tk_set['_id'], **tk_set})
        return TK_SETTINGS
