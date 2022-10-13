from typing import Optional, Union

from pydantic import BaseModel, Field

from app.exceptions import TkError


class TKOrderParams(BaseModel):
    id: int
    force: bool = False
    insurance: bool = False
    hardPacking: bool = False


class CreateApplicationRequest(BaseModel):
    cargopickup: bool
    arr: list[TKOrderParams]
    test: bool = False


class CreateApplicationInfo(BaseModel):
    id: Optional[int]
    error: Optional[str]
    tk_num: Optional[str]


class TKCreateApplicationAsync(BaseModel):
    """
    {'access_token': строка с токеном}
    """

    token: str


class TKCreateApplicationRequest(BaseModel):
    """
    Дефолтная заявка в сервис
    """

    cargopickup: bool = True
    arr: list[TKOrderParams]
    test: bool = False


class CreateApplicationResponse(BaseModel):
    info: list[Union[CreateApplicationInfo, TkError]] = Field(default_factory=list)
    file: str = ""
    file_cargo: str = ""
    error: Optional[str]


class TKOneIteration(BaseModel):
    class PDF(BaseModel):
        info: Optional[bytes]
        cargo: Optional[bytes]

    response: Union[CreateApplicationInfo, TkError] = None
    is_success: bool = False
    pdf: PDF = PDF()
