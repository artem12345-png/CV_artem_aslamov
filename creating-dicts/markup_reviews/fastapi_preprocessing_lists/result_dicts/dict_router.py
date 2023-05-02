import ast
import datetime
import os

import humanize
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from fastapi_pagination import LimitOffsetPage, LimitOffsetParams, paginate
from services.check_hashed_pass import get_password_hash, verify_password
from services.creditionals import DB
from services.query import query, get_second_part, total_reviews, meta_data, sum_working_time
from sqlalchemy import func

from .settings import database, models, schemas
from .settings.exceptions import NotAuthenticatedException
from .settings.models import Reviews
from .settings.schemas import Page as DomainPage
from .settings.schemas import PostMarkupDiff, ReviewsMarkupGet
from .settings.utils import domains_mkup, prepare_queries

router = APIRouter()
templates = Jinja2Templates(
    directory="templates",
    autoescape=False,
    auto_reload=True,
)
templates.env.globals["humanize"] = humanize

SECRET = os.urandom(24).hex()

manager = LoginManager(
    SECRET,
    token_url="/login/auth",
    use_cookie=True,
    custom_exception=NotAuthenticatedException,
)
manager.cookie_name = "login_cookie"


@manager.user_loader
def load_user(username: str):
    user = DB.get(username)
    return user


# stopped
'''@router.get("/load_data_in_database/{domain_id}/{lang}/{progon}")
async def process_ngramms(domain_id: str, lang: str, progon: str) -> Dict:
    """Загрузка данных из скрипта в базу данных"""

    os.chdir(os.path.abspath('../preprocessing_lists'))
    os.system(
        f"python main_preprocessing_lists.py {domain_id} {lang} {progon}"
    )
    return {
        "info": "ok",
        "domain": domain_id,
        "lang": lang,
    }'''


@router.get(
    "/reviews",
    response_model=schemas.Page[schemas.ReviewsGet],
    response_class=HTMLResponse,
)
def get_reviews(
    request: Request,
    _=Depends(manager),
):
    """Получить все дефолтные отзывы."""
    MAX_ITEM_LIMIT = 1000
    template = "reviews.html"
    reviews = database.session.query(Reviews).limit(MAX_ITEM_LIMIT).all()
    paginated_obg = paginate(reviews).__dict__
    reviews = paginated_obg.get("items")
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "reviews": reviews,
        },
    )


@router.post(
    "/reviews",
    response_model=schemas.Page[schemas.ReviewsGet],
    response_class=HTMLResponse,
)
def post_reviews(
    request: Request,
    form_data: schemas.PostFormModel = Depends(schemas.PostFormModel.as_form),
    _=Depends(manager),
):
    """Отправить форму и получить отфильтрованные запросы."""

    MAX_ITEM_LIMIT = 10000
    form = request.__dict__.get("_form").__dict__["_dict"]
    comment = form.get("comment_text")
    domain = int(form.get("domain_id"))
    template = "reviews.html"
    query = database.session.execute(
        f"""select * from texts
        where domain_id = {domain} and comment_text
        ILIKE '%{comment}%' LIMIT {MAX_ITEM_LIMIT};"""
    )
    paginate_obg = paginate(query.all()).__dict__
    reviews = paginate_obg.get("items")

    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "reviews": reviews,
        },
    )


@router.get("/domains", response_model=DomainPage[schemas.DomainsGet])
def get_domains():
    """Получает все домены и их id"""

    results = database.session.query(models.Domains).all()
    return paginate(results)


@router.get("/markup_reviews")
def get_markup_reviews(request: Request, _=Depends(manager)):
    query = request.query_params._dict
    template = "reviews_markups.html"
    list_domain_names = domains_mkup()
    counter_one = database.session.execute(
        "select DISTINCT counter from markup_reviews order by counter desc"
    ).fetchone()
    if not query:
        query = dict(counters=counter_one[0])
    if not query.get("counters"):
        query["counters"] = counter_one[0]
    counter = database.session.execute(
        "select DISTINCT counter from markup_reviews order by counter desc"
    ).all()
    overall_sentiment_label = database.session.execute(
        "select DISTINCT sentiment_label "
        "from markup_reviews order by sentiment_label"
    ).all()
    overall_text_label = database.session.execute(
        "select DISTINCT text_sentiment_label "
        "from markup_reviews order by text_sentiment_label"
    ).all()
    rating_db = database.session.execute(
        "select DISTINCT rating " "from markup_reviews order by rating"
    ).all()
    query_db = (
        database.session.query(
            models.MarkupReviews.text_id,
            models.MarkupReviews.comment_text,
            models.MarkupReviews.dict_name,
            models.MarkupReviews.ton_dictionary,
            func.groupArray(models.MarkupReviews.topic_name).label("topic_name"),
            func.groupArray(models.MarkupReviews.phrases).label("phrases"),
            func.groupArray(models.MarkupReviews.sentiment_label).label(
                "sentiment_label"
            ),
            func.groupArray(models.MarkupReviews.topic_id).label("topic_id"),
            func.groupArray(models.MarkupReviews.clients_theme_id).label(
                "clients_theme_id"
            ),
            func.groupArray(models.MarkupReviews.theme_from_clients).label(
                "theme_from_clients"
            ),
            func.groupArray(models.MarkupReviews.theme_from_theme).label(
                "theme_from_theme"
            ),
            models.MarkupReviews.text_sentiment_label,
            models.MarkupReviews.counter,
            models.MarkupReviews.domain_id,
            models.MarkupReviews.segmentation,
            models.MarkupReviews.topics,
            models.MarkupReviews.lemmas,
            models.MarkupReviews.rating,
            models.Domains.name,
        )
        .filter(models.Domains.id == models.MarkupReviews.domain_id)
        .group_by(
            models.MarkupReviews.text_id,
            models.MarkupReviews.comment_text,
            models.MarkupReviews.dict_name,
            models.MarkupReviews.ton_dictionary,
            models.MarkupReviews.text_sentiment_label,
            models.MarkupReviews.counter,
            models.MarkupReviews.domain_id,
            models.MarkupReviews.segmentation,
            models.MarkupReviews.topics,
            models.MarkupReviews.lemmas,
            models.MarkupReviews.rating,
            models.Domains.name,
        )
    )
    query_db = prepare_queries(
        query=query, query_db=query_db, model=models.MarkupReviews
    )
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "reviews": query_db.order_by(models.MarkupReviews.counter.desc()).limit(
                100
            ),
            "id": query.get("id"),
            "comment_text": query.get("comment_text"),
            "query_domain": query.get("domain_id"),
            "phrases": query.get("phrases"),
            "theme": query.get("theme"),
            "sentiment_label": query.get("sentiment_label"),
            "text_sentiment_label": query.get("text_sentiment_label"),
            "counters": query.get("counters"),
            "domains": list_domain_names,
            "counter": counter,
            "overall_sentiment_label": overall_sentiment_label,
            "overall_text_label": overall_text_label,
            "urls": request.url_for("get_markup_reviews"),
            "rating_db": rating_db,
            "len": len,
            "ast": ast,
        },
    )


@router.get("/markup_reviews/run/{counter}", response_class=HTMLResponse)
def get_markup_counter_by_int(request: Request, counter: int, _=Depends(manager)):
    runs = (
        database.session.query(
            models.MarkupInfo.counter_id,
            models.MarkupInfo.markup_version,
            models.MarkupInfo.run_date,
            func.sum(models.MarkupInfo.nulls_phrases).label("nulls_phrases"),
            func.sum(models.MarkupInfo.nulls_topics).label("nulls_topics"),
            func.sum(models.MarkupInfo.working_time).label("working_time"),
            func.sum(models.MarkupInfo.reviews_count).label("reviews_count"),
            models.MarkupInfo.topic_dictionary,
            models.MarkupInfo.ton_dictionary,
            models.MarkupInfo.domain_id,
            models.MarkupInfo.reviews_to_process,
            func.sum(models.MarkupInfo.negative_overall).label("negative_overall"),
            func.sum(models.MarkupInfo.positive_overall).label("positive_overall"),
            func.sum(models.MarkupInfo.neutral_overall).label("neutral_overall"),
            models.Domains.name,
        )
        .filter(models.MarkupInfo.counter_id == counter)
        .group_by(
            models.MarkupInfo.counter_id,
            models.MarkupInfo.reviews_to_process,
            models.MarkupInfo.markup_version,
            models.MarkupInfo.run_date,
            models.MarkupInfo.topic_dictionary,
            models.MarkupInfo.ton_dictionary,
            models.MarkupInfo.domain_id,
            models.Domains.name,
        )
        .filter(
            models.MarkupInfo.domain_id == models.Domains.id,
        )
        .order_by(models.MarkupInfo.counter_id.desc())
        .all()
    )
    template = "markup_info.html"
    return templates.TemplateResponse(
        template, {"request": request, "runs": runs, "datetime": datetime}
    )


#  _=Depends(manager)
@router.get("/markup_reviews/runs_info", response_class=HTMLResponse)
def get_markup_counters(request: Request, _=Depends(manager)):
    runs = (
        database.session.query(
            models.MarkupInfo.counter_id,
            models.MarkupInfo.markup_version,
            models.MarkupInfo.run_date,
            func.sum(models.MarkupInfo.nulls_phrases).label("nulls_phrases"),
            func.sum(models.MarkupInfo.nulls_topics).label("nulls_topics"),
            func.sum(models.MarkupInfo.working_time).label("working_time"),
            func.sum(models.MarkupInfo.reviews_count).label("reviews_count"),
            models.MarkupInfo.topic_dictionary,
            models.MarkupInfo.ton_dictionary,
            models.MarkupInfo.domain_id,
            models.MarkupInfo.reviews_to_process,
            func.sum(models.MarkupInfo.negative_overall).label("negative_overall"),
            func.sum(models.MarkupInfo.positive_overall).label("positive_overall"),
            func.sum(models.MarkupInfo.neutral_overall).label("neutral_overall"),
            models.Domains.name,
        )
        .group_by(
            models.MarkupInfo.counter_id,
            models.MarkupInfo.reviews_to_process,
            models.MarkupInfo.markup_version,
            models.MarkupInfo.run_date,
            models.MarkupInfo.topic_dictionary,
            models.MarkupInfo.ton_dictionary,
            models.MarkupInfo.domain_id,
            models.Domains.name,
        )
        .filter(
            models.MarkupInfo.domain_id == models.Domains.id,
        )
        .order_by(models.MarkupInfo.counter_id.desc())
        .all()
    )
    template = "markup_info.html"
    return templates.TemplateResponse(
        template, {"request": request, "runs": runs, "datetime": datetime}
    )


@router.get("/login", response_class=HTMLResponse)
def loginwithCreds(request: Request):
    template = "login.html"
    return templates.TemplateResponse(
        template,
        {
            "request": request,
        },
    )


@router.get("/markup_reviews/get_diff", response_class=HTMLResponse)
def get_difference_get(request: Request, _=Depends(manager)):
    template = "diff.html"
    return templates.TemplateResponse(
        template,
        {
            "request": request,
        },
    )


@router.post("/markup_reviews/get_diff", response_class=HTMLResponse)
def get_difference_post(
    request: Request,
    _=Depends(manager),
    form_data: PostMarkupDiff = Depends(PostMarkupDiff.as_form),
):
    # TODO давай вынесем это на уровень модуля в TEMPLATE и будем поделючать в dict
    template = "diff.html"
    first_run = form_data.run_1
    second_run = form_data.run_2

    working_times = database.session.execute(
        sum_working_time.format(progon_1=first_run, progon_2=second_run)
    )
    working_times = working_times.fetchall()

    meta_dt = database.session.execute(
        meta_data.format(progon_1=first_run, progon_2=second_run)
    )
    meta_dt = meta_dt.fetchall()

    total_revs = database.session.execute(
        total_reviews.format(progon_1=first_run, progon_2=second_run)
    )
    total_revs = total_revs.fetchall()

    result = database.session.execute(
        get_second_part.format(progon_1=first_run, progon_2=second_run)
    )
    result = result.fetchall()
    try:
        fr_working_time = working_times[0][1]
        sr_working_time = working_times[1][1]
        fr_working_time = datetime.datetime.fromtimestamp(fr_working_time-7*60*60).strftime("%H:%M:%S")
        sr_working_time = datetime.datetime.fromtimestamp(sr_working_time - 7 * 60 * 60).strftime("%H:%M:%S")
        fr_markup_version = meta_dt[0][1]
        fr_topic_dictionary = meta_dt[0][2]
        fr_ton_dictionary = meta_dt[0][3]
        fr_domain_id = meta_dt[0][4]
        fr_run_date = meta_dt[0][5]
        sr_markup_version = meta_dt[1][1]
        sr_topic_dictionary = meta_dt[1][2]
        sr_ton_dictionary = meta_dt[1][3]
        sr_domain_id = meta_dt[1][4]
        sr_run_date = meta_dt[1][5]
        total_revs_run1 = total_revs[0][1]
        total_revs_run2 = total_revs[1][1]
        fr_nulls_phrases = result[0][1] if result[0][1] else 0
        sr_nulls_phrases = result[1][1] if result[1][1] else 0
        fr_negative = result[0][2] if result[0][2] else 0
        sr_negative = result[1][2] if result[1][2] else 0
        fr_positive = result[0][3] if result[0][3] else 0
        sr_positive = result[1][3] if result[1][3] else 0
        fr_neutral = result[0][4] if result[0][4] else 0
        sr_neutral = result[1][4] if result[1][4] else 0
        fr_all_phrases = fr_negative + fr_positive + fr_neutral
        sr_all_phrases = sr_negative + sr_positive + sr_neutral
        fr_theme_null_reviews_total_percent = fr_nulls_phrases / total_revs_run1 * 100
        sr_theme_null_reviews_total_percent = sr_nulls_phrases / total_revs_run2 * 100
        fr_negative_percent, sr_negative_percent = (
            fr_negative / fr_all_phrases * 100,
            sr_negative / sr_all_phrases * 100,
        )
        fr_positive_percent, sr_positive_percent = (
            fr_positive / fr_all_phrases * 100,
            sr_positive / sr_all_phrases * 100,
        )
        fr_neutral_percent, sr_neutral_percent = (
            fr_neutral / fr_nulls_phrases * 100,
            sr_neutral / sr_nulls_phrases * 100,
        )
        diff_negative_percent = sr_negative_percent - fr_negative_percent
        percent_diff_negative_phrases = diff_negative_percent / fr_negative_percent * 100
        diff_positive_percent = sr_positive_percent - fr_positive_percent
        percent_diff_positive_phrases = diff_positive_percent / fr_positive_percent * 100
        diff_neutral_percent = sr_neutral_percent - fr_neutral_percent
        percent_diff_neutral_phrases = diff_neutral_percent / fr_neutral_percent * 100
        diff_total = total_revs_run2 - total_revs_run1
        diff_total_reviews_percent = (diff_total / total_revs_run1 * 100)
        diff_theme_null_reviews_total_percent = (
            sr_theme_null_reviews_total_percent - fr_theme_null_reviews_total_percent
        )
        percent_diff_nulls_theme = diff_theme_null_reviews_total_percent / fr_theme_null_reviews_total_percent * 100
        diff_all_phrases = sr_all_phrases - fr_all_phrases
        diff_all_phrases_percent = (
            diff_all_phrases / total_revs_run1 * 100
        )

        return templates.TemplateResponse(
            template,
            dict(
                request=request,
                result=result,
                first_run=first_run,
                second_run=second_run,
                fr_nulls_phrases=fr_nulls_phrases,
                sr_nulls_phrases=sr_nulls_phrases,
                fr_negative=fr_negative,
                sr_negative=sr_negative,
                fr_positive=fr_positive,
                sr_positive=sr_positive,
                fr_neutral=fr_neutral,
                sr_neutral=sr_neutral,
                fr_all_phrases=fr_all_phrases,
                sr_all_phrases=sr_all_phrases,
                fr_theme_null_reviews_total_percent=round(
                    fr_theme_null_reviews_total_percent, 2
                ),
                sr_theme_null_reviews_total_percent=round(
                    sr_theme_null_reviews_total_percent, 2
                ),
                fr_negative_percent=round(fr_negative_percent, 2),
                sr_negative_percent=round(sr_negative_percent, 2),
                fr_positive_percent=round(fr_positive_percent, 2),
                sr_positive_percent=round(sr_positive_percent, 2),
                fr_neutral_percent=round(fr_neutral_percent, 2),
                sr_neutral_percent=round(sr_neutral_percent, 2),
                diff_negative_percent=round(diff_negative_percent, 2),
                diff_positive_percent=round(diff_positive_percent, 2),
                diff_neutral_percent=round(diff_neutral_percent, 2),
                diff_total_reviews_percent=round(diff_total_reviews_percent, 2),
                diff_theme_null_reviews_total_percent=round(
                    diff_theme_null_reviews_total_percent, 2
                ),
                diff_all_phrases=round(diff_all_phrases, 2),
                diff_all_phrases_percent=round(diff_all_phrases_percent, 2),
                total_revs_run1=total_revs_run1,
                total_revs_run2=total_revs_run2,
                diff_total=diff_total,
                percent_diff_nulls_theme=round(percent_diff_nulls_theme, 2),
                percent_diff_negative_phrases=round(percent_diff_negative_phrases, 2),
                percent_diff_positive_phrases=round(percent_diff_positive_phrases, 2),
                percent_diff_neutral_phrases=round(percent_diff_neutral_phrases, 2),
                fr_markup_version=fr_markup_version,
                fr_topic_dictionary=fr_topic_dictionary,
                fr_ton_dictionary=fr_ton_dictionary,
                fr_domain_id=fr_domain_id,
                sr_markup_version=sr_markup_version,
                sr_topic_dictionary=sr_topic_dictionary,
                sr_ton_dictionary=sr_ton_dictionary,
                sr_domain_id=sr_domain_id,
                fr_run_date=fr_run_date,
                sr_run_date=sr_run_date,
                fr_working_time=fr_working_time,
                sr_working_time=sr_working_time
            ),
        )
    except Exception as e:
        return templates.TemplateResponse(
            template,
            dict(
                request=request,
                result=result,
                first_run=first_run,
                second_run=second_run,
            ),
        )


@router.get("/markup_reviews/get_more_diff", response_class=HTMLResponse)
def get_difference_more_get(request: Request, _=Depends(manager)):
    template = "get_more_diff.html"
    return templates.TemplateResponse(
        template,
        {
            "request": request,
        },
    )


@router.post("/markup_reviews/get_more_diff", response_class=HTMLResponse)
def get_difference_more_post(
    request: Request,
    _=Depends(manager),
    form_data: PostMarkupDiff = Depends(PostMarkupDiff.as_form),
):
    # TODO давай вынесем это на уровень модуля в TEMPLATE и будем поделючать в dict
    template = "get_more_diff.html"
    first_run = form_data.run_1
    second_run = form_data.run_2
    result = database.session.execute(
        query.format(progon_1=first_run, progon_2=second_run)
    )
    result = result.fetchall()

    return templates.TemplateResponse(
        template,
        dict(
            request=request,
            result=result,
            first_run=first_run,
            second_run=second_run,
        ),
    )


@router.post("/login/auth")
def login(data: OAuth2PasswordRequestForm = Depends()):
    username = data.username
    password = get_password_hash(data.password)
    user = load_user(username)
    if not user:
        raise InvalidCredentialsException
    if not verify_password(user["password"], password):
        raise InvalidCredentialsException
    access_token = manager.create_access_token(data={"sub": username})
    resp = RedirectResponse(url="/markup_reviews", status_code=status.HTTP_302_FOUND)
    manager.set_cookie(resp, access_token)
    return resp
