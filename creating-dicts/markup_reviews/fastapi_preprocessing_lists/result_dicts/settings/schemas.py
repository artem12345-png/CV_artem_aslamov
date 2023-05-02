"""Схемы для моделей и response."""
from datetime import date
from typing import Generic, Optional, TypeVar, Union

from fastapi import Form, Query
from fastapi_pagination.default import Page as BasePage
from fastapi_pagination.default import Params as BaseParams
from pydantic import UUID4, BaseModel

T = TypeVar("T")  # Для pages params


def f(x: date):
    pass


class PostMarkupDiff(BaseModel):
    """POST form Pydantic model, where variables are forms to input."""

    run_1: int = 0
    run_2: int = 0

    @classmethod
    def as_form(
        cls,
        run_1: int = Form(...),
        run_2: int = Form(...),
    ):
        return cls(run_1=run_1, run_2=run_2)


class ReviewsGet(BaseModel):
    """Ответная форма получения данных
    из базы данных."""

    id: int
    comment_text: str
    rating: Optional[int] = None
    org_id: Optional[int] = None
    date: Union[date, None]
    commentid: Optional[str] = None
    user_name: Optional[str] = None
    source_id: Optional[int] = None
    markup_data: Optional[str] = None
    typos_corrected_text: Optional[str] = None
    lemmatized_text: Optional[str] = None
    typos_corrected: Optional[int] = None
    domain_id: int
    google_org_id: Union[int, str] = None
    markup_info: Optional[str] = None
    text_info: Optional[int] = None
    additional_info: Optional[str] = None
    source_category: Optional[str] = None

    class Config:
        orm_mode = True


class ReviewsMarkupGet(BaseModel):
    """Ответная форма получения данных
    из базы данных."""

    id: UUID4
    text_id: str
    comment_text: Optional[str] = None
    markup_date: Optional[Union[date, None]] = None
    dict_name: Optional[str] = None
    ton_dictionary: Optional[str] = None
    topic_name: Optional[str] = None
    sentiment_label: Optional[str] = None
    text_sentiment_label: Optional[str] = None
    counter: Optional[Union[int, str]] = None
    domain_id: Optional[Union[int, str]] = None
    batch_num: Optional[Union[int, str]] = None
    processed_dttm: Union[date, None] = None
    phrases: Optional[list[str]] = None
    segmentation: Optional[str] = None
    topics: Optional[str] = None
    lemmas: Optional[str] = None
    topic_id: Optional[Union[int, str]] = None
    theme_from_theme: Optional[Union[int, str]] = None
    theme_from_clients: Optional[Union[int, str]] = None
    clients_theme_id: Optional[int] = None

    class Config:
        orm_mode = True


class DomainsGet(BaseModel):
    """Ответная форма получения данных
    из базы данных."""

    id: int
    name: str

    class Config:
        orm_mode = True


class PostFormModel(BaseModel):
    """Модель отправки формы."""

    comment_text: Optional[str] = None
    domain_id: int

    @classmethod
    def as_form(cls, comment_text: str = Form(...), domain_id: int = Form(...)):
        return cls(comment_text=comment_text, domain_id=domain_id)


class Params(BaseParams):
    """Переназначение параметров пагинации."""

    size: int = Query(1000, ge=1, le=2_000, description="Page size")


class Page(BasePage[T], Generic[T]):
    """Переназначение параметров страницы с
    новыми параметрами пагинации."""

    __params_type__ = Params
