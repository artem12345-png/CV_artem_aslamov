from fastapi import HTTPException

from app.settings.log import logger, format_log_message


async def cargopick_checker(_request, request):
    if not request.cargopickup:
        logger.warning(
            await format_log_message(
                _request,
                dict(error="Метод не реализован для предварительной заявки"),
                has_body=True,
            )
        )
        raise HTTPException(
            status_code=400, detail="Метод не реализован для предварительной заявки"
        )


async def null_data_checker(_request, request):
    if not request.arr:
        logger.warning(
            await format_log_message(
                _request, dict(error="Не были переданы данные"), has_body=True
            )
        )
        raise HTTPException(status_code=400, detail="Не были переданы данные")
