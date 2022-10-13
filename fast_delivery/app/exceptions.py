from pydantic import BaseModel


class FillerException(Exception):
    pass


class OrderNotExistsException(FillerException):
    pass


class CityNotDefinedException(FillerException):
    pass


class TerminalNotFoundException(FillerException):
    pass


class NoAddressException(FillerException):
    pass


class NoTKException(FillerException):
    def __init__(self, idmonopolia):
        msg = f"У заказа не указана ТК, idmonopolia={idmonopolia}"
        super(NoTKException, self).__init__(msg)


class EmptyStockAddressException(FillerException):
    pass


class CityIsNotFilial(FillerException):
    pass


class TransportAPIException(Exception):
    pass


class IntakesException(TransportAPIException):
    pass


class IntakesExistsException(IntakesException):
    def __init__(self):
        super().__init__(
            "Заявка на консолидированный забор груда на сегодня уже создана. "
            "Оформленные заявки будут включены в следующую "
            "заявку, которая оформляется раз в день при отправке."
        )


class TransportAPITimeOutException(Exception):
    pass


class TkError(BaseModel):
    id: int
    error: str


class NoCookieException(Exception):
    pass


class CountTerminalsException(Exception):
    def __init__(self, count):
        super().__init__(
            f"В указанном городе {count} терминалов." + ""
            if count == 0
            else "Необходимо указать один из них."
        )
