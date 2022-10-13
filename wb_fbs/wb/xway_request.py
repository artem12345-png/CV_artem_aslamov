import logging
from enum import Enum

import httpx

from env import SERVICE_NAME, SETTINGS

logger = logging.getLogger(SERVICE_NAME)


class RequestType(Enum):
    post = "post"
    get = "get"
    patch = "patch"
    put = "put"
    delete = "delete"


async def log_request(
    client: httpx.AsyncClient,
    url: str,
    request_body: dict | None = None,
    method: RequestType = RequestType.post,
    additional_headers: dict | None = None,
    *,
    is_long_resp=False,
):
    assert "http" in url, "http absent in URL"

    async_request_function = getattr(client, method.value)
    function_params = {
        "json": request_body,
        "headers": additional_headers,
    }
    if method == RequestType.get or request_body is None:
        del function_params["json"]

    response: httpx.Response = await async_request_function(url, **function_params)

    content_result = response.content
    try:
        content_result = content_result.decode()
    except Exception as e:
        logger.exception(f"При декодировании ответа возникла ошибка: {e}")

    if is_long_resp:
        content_result = content_result[:200]

    logger.info(
        f"{method.value.upper()} {url} body={request_body} response={content_result}"
    )
    return response


async def xway_request(api_method, method: RequestType, body=None, is_long_resp=False):
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await log_request(
            client,
            f"{SETTINGS.XWAY_URL}{api_method}",
            body,
            method,
            additional_headers={"authorization": f"Token {SETTINGS.XWAY_TOKEN}"},
            is_long_resp=is_long_resp,
        )
    return response
