import httpx

from ozon.simple_functions import delete_none


class ApiBase:
    def __init__(self, headers, url, logger=None):
        self.logger = logger
        self.headers = headers
        self.url = url

    def _log(self, content, type_of_message="info"):
        if not self.logger:
            print(content)
        else:
            if type_of_message == "info":
                self.logger.info(content)
            elif type_of_message == "error":
                self.logger.error(content, exc_info=True)
            elif type_of_message == "exception":
                assert isinstance(content, Exception)
                self.logger.exception(content)
            else:
                raise ValueError(
                    f"This type of message doesn't implemented: {type_of_message}"
                )

    async def _post(
        self,
        client: httpx.AsyncClient,
        method,
        body,
        is_long_resp=False,
        raw=False,
        exclude_none=True,
    ):
        if exclude_none:
            body = delete_none(body)

        url = self.url + method
        self._log(f"POST {url}, body={body}")
        response = await client.post(
            url, json=body, headers=self.headers, timeout=60 * 20
        )
        if is_long_resp:
            content_log = response.content[:100]
        else:
            content_log = response.content

        try:
            content_log = content_log.decode() if isinstance(content_log, bytes) else content_log  # type: ignore
        except UnicodeDecodeError:
            pass
        self._log(f"POST {url}, body={body}, response={content_log}")  # type: ignore

        response.raise_for_status()
        if raw:
            result = response.content
        else:
            result = response.json()

        return result
