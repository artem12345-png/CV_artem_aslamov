from sqlalchemy import text

from .database import cursor
from .models import MarkupReviews


def prepare_queries(query, query_db, model):
    if query.get("id"):
        id = query.get("id")
        query_db = query_db.filter(model.text_id.like(f"{id}"))
    if query.get("comment_text"):
        comment_text = query.get("comment_text")
        query_db = query_db.filter(model.comment_text.ilike(f"%{comment_text}%"))
    if query.get("theme"):
        theme = query.get("theme")
        query_db = query_db.filter(model.topic_name.ilike(f"%{theme}%"))
    if query.get("phrases"):
        phrase = query.get("phrases")
        query_db = query_db.where(
            text(
                "not empty(arrayFilter(x -> x ILIKE "
                f"'{phrase}', {MarkupReviews.__tablename__}.phrases))"
            )
        )
    if query.get("domain_id"):
        domain_id = int(query.get("domain_id").split(" - ")[1])
        query_db = query_db.filter(model.domain_id == domain_id)
    if query.get("sentiment_label"):
        sentiment_label = query.get("sentiment_label")
        query_db = query_db.filter(model.sentiment_label.ilike(f"%{sentiment_label}%"))
    if query.get("text_sentiment_label"):
        text_sentiment_label = query.get("text_sentiment_label")
        query_db = query_db.filter(
            model.text_sentiment_label.ilike(f"%{text_sentiment_label}%")
        )
    if query.get("counters"):
        counter = int(query.get("counters"))
        query_db = query_db.filter(model.counter == counter)
    if query.get("rating") and query.get("rating") != "None":
        rating = float(query.get("rating"))
        query_db = query_db.filter(model.rating == rating)
    return query_db


def domains():
    domain_ids = []
    cursor.execute("SELECT * FROM business_domain")
    for i in cursor.fetchall():
        domain_ids.append(" - ".join([str(x) for x in i]))
    return domain_ids


def domains_mkup():
    domain_ids = []
    cursor.execute(
        """
        SELECT DISTINCT b.name, m.domain_id FROM markup_reviews m
        INNER JOIN business_domain b on b.id = m.domain_id
        ORDER BY m.domain_id desc
        """
    )
    for i in cursor.fetchall():
        domain_ids.append(" - ".join([str(x) for x in i]))
    return domain_ids
