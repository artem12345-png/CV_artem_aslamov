from typing import Optional

from pydantic import BaseModel


class StatusApplication(BaseModel):
    """
    Чтобы не переделывать нашу основную заявку
    """

    idmonopolia: int
    tk_num: str
    # Статус груза в ТК
    status: Optional[str] = None
