from app.settings.consts import TK_TRACK_URL, TK_ID_NAME


class SMSFormatter:
    def __init__(self, idtk: int):
        self.idtk = idtk

    def format(self, tk_num, idmonopolia):
        return (
            f"Ваш заказ {idmonopolia} передан в компанию {TK_ID_NAME[self.idtk]} для отслеживания "
            f"груза используйте код {tk_num} Узнать состояние груза "
            f"{TK_TRACK_URL[self.idtk]({'tk_num': tk_num})} "
            f"Телефон 8 800 5552123"
        )
