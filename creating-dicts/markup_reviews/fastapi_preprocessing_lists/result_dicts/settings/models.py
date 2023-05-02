"""Модуль настроек моделей и таблиц."""
from clickhouse_sqlalchemy import engines, types
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ARRAY

from .database import Base


class Reviews(Base):
    __tablename__ = "texts"
    id = Column(types.Int64, primary_key=True)
    comment_text = Column(types.String)
    domain_id = Column(types.Int64)
    __table_args__ = (engines.MergeTree(),)


class Domains(Base):
    __tablename__ = "business_domain"
    id = Column(types.Int64, primary_key=True)
    name = Column(types.String)
    __table_args__ = (engines.MergeTree(),)


class MarkupReviews(Base):
    __tablename__ = "markup_reviews"
    id = Column(types.UUID, primary_key=True)
    text_id = Column(types.Int64)
    comment_text = Column(types.String)
    rating = Column(types.Float32)
    topic_name = Column(types.String)
    phrases = Column(ARRAY(types.String))
    ton_dictionary = Column(types.String)
    domain_id = Column(types.Int64)
    counter = Column(types.UInt64)
    sentiment_label = Column(types.String)
    dict_name = Column(types.String)
    text_sentiment_label = Column(types.String)
    segmentation = Column(types.String)
    topics = Column(types.String)
    lemmas = Column(types.String)
    topic_id = Column(types.Int64)
    theme_from_theme = Column(types.String)
    theme_from_clients = Column(types.String)
    clients_theme_id = Column(types.Int64)
    __table_args__ = (engines.MergeTree(),)


class MarkupInfo(Base):
    __tablename__ = "markup_reviews_run_info"
    counter_id = Column(types.UInt64, primary_key=True)
    markup_version = Column(types.String)
    run_date = Column(types.Date)
    working_time = Column(types.Float32)
    nulls_phrases = Column(types.Int64)
    nulls_topics = Column(types.Int64)
    reviews_count = Column(types.String)
    topic_dictionary = Column(types.String)
    ton_dictionary = Column(types.String)
    domain_id = Column(types.Int64)
    negative_overall = Column(types.Int64)
    positive_overall = Column(types.Int64)
    neutral_overall = Column(types.Int64)
    reviews_to_process = Column(types.UInt64)
    __table_args__ = (engines.MergeTree(),)
