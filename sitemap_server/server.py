import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from app.tools import init_logging, sitemap, goods, cats, articles, firms, news
from app.env_conf import SETTINGS
from app.consts import d_site, list_subdomain

app = FastAPI()

# ________________________________________________________________________________________________________________


@app.get("/self_check")
async def self_check():
    """ \n
     Функция для проверки работоспособности всего микросервиса
        - На вход ничего не поступает
        - Возвращает просто словарь с ключем "status" и значением "Ok"
    """
    return {"status": "Ok"}


# ________________________________________________________________________________________________________________


@app.get("/sitemap/{site}/{subdomain}", status_code=400)
def get_sitemap(site: str, subdomain: str):

    if not (d_site.get(site) and subdomain in list_subdomain):
        return

    return Response(content=sitemap(site, subdomain), media_type="text/XML")

# ________________________________________________________________________________________________________________


@app.get("/sitemap_goods/{site}/{subdomain}/{quantity}", status_code=400)
def get_goods(site: str, subdomain: str, quantity: int):

    if not (d_site.get(site) and subdomain in list_subdomain):
        return

    return Response(content=goods(site, subdomain, quantity), media_type="text/XML")


# ________________________________________________________________________________________________________________


@app.get("/sitemap_cats/{site}/{subdomain}", status_code=400)
def get_cats(site: str, subdomain: str):

    if not (d_site.get(site) and subdomain in list_subdomain):
        return

    return Response(content=cats(site, subdomain), media_type="text/XML")

# ________________________________________________________________________________________________________________


@app.get("/sitemap_articles/{site}/{subdomain}", status_code=400)
def get_articles(site: str, subdomain: str):

    if not (d_site.get(site) and subdomain in list_subdomain):
        return

    return Response(content=articles(site, subdomain), media_type="text/XML")

# ________________________________________________________________________________________________________________


@app.get("/sitemap_firms/{site}/{subdomain}", status_code=400)
def get_firms(site: str, subdomain: str):

    if not (d_site.get(site) and subdomain in list_subdomain):
        return

    return Response(content=firms(site, subdomain), media_type="text/XML")

# ________________________________________________________________________________________________________________


@app.get("/sitemap_news/{site}/{subdomain}", status_code=400)
def get_cats(site: str, subdomain: str):

    if not (d_site.get(site) and subdomain in list_subdomain):
        return

    return Response(content=news(site, subdomain), media_type="text/XML")


# ________________________________________________________________________________________________________________


def init_app(use_sentry=True):
    init_logging(use_sentry=use_sentry)


def run():
    init_app(use_sentry=not SETTINGS.DEBUG)

    uvicorn.run(app, host="0.0.0.0", port=8008)


if __name__ == "__main__":
    run()
