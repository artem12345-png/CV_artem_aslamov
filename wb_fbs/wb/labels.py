import base64
import io
import logging
import tempfile
from functools import lru_cache
from pathlib import Path

import aioboto3
import pikepdf
from PyPDF3 import PdfFileReader, PdfFileWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from env import SETTINGS, BUCKET_NAME_S3
from wb.xway_request import xway_request, RequestType

logger = logging.getLogger(SETTINGS.SERVICE_NAME)


async def get_labels(order_id: int) -> io.BytesIO | None:
    # https://wiki.xway.ru/docs/poluchenie-jetiketki-na-zakaz-2/
    response = await xway_request(
        method=RequestType.post,
        api_method="/api/v1/orders/label/",
        body={"posting_number": order_id},
        is_long_resp=True,
    )
    file_json = response.json()
    if response.status_code == 200:
        file = io.BytesIO(base64.b64decode(file_json[0]["file"]))
        return file
    else:
        logger.exception(f"Не удалось получить наклейки для order_id={order_id}")


def modify_cargo_pdf(
    pdf_io: io.BytesIO,
    idmonopolia: int,
    item_name: str,
    artikul: str,
    date_delivery: str,
    font_size=5,
) -> io.BytesIO:
    packet = io.BytesIO()
    # create a new PDF with Reportlab
    can = canvas.Canvas(packet, pagesize=letter)
    pdfmetrics.registerFont(TTFont("FreeSans", "FreeSans.ttf"))
    pdfmetrics.registerFont(TTFont("CalibriBold", "calibri_bold.ttf"))
    # Вариант 1
    can.setFont("CalibriBold", font_size)
    can.drawString(7, 80, f"№{idmonopolia}")
    can.setFont("FreeSans", font_size)
    can.drawString(35, 80, f"{artikul} # {item_name[:19]}")

    can.setFont("CalibriBold", font_size)
    can.drawString(7, 24, f"Отгрузить WB до {date_delivery}")

    can.save()

    # move to the beginning of the StringIO buffer
    packet.seek(0)
    new_pdf = PdfFileReader(packet)
    # read your existing PDF

    try:
        existing_pdf = PdfFileReader(pdf_io, strict=False)
        page = existing_pdf.getPage(0)
    except ValueError:
        # возникает ошибка, как будто ПДФ сломанный
        # (функция getPage(0) -> int with base 10 b"...")
        pdf_io.seek(0)
        pdf = pikepdf.open(pdf_io)
        buff = io.BytesIO()
        pdf.save(buff)
        existing_pdf = PdfFileReader(buff)
        page = existing_pdf.getPage(0)

    output = PdfFileWriter()
    # add the "watermark" (which is the new pdf) on the existing page
    page.mergePage(new_pdf.getPage(0))
    output.addPage(page)
    # finally, write "output" to a real file
    output_stream = io.BytesIO()
    output.write(output_stream)
    output_stream.seek(0)
    return output_stream


async def get_object(bucket: str, filename: str) -> Path:
    session = get_session()
    async with session.client(
        "s3",
        aws_access_key_id=SETTINGS.aws_access_key_id,
        aws_secret_access_key=SETTINGS.aws_secret_access_key,
        endpoint_url=SETTINGS.ENDPOINT_S3,
    ) as s3:
        temp_filename = next(tempfile._get_candidate_names()) + ".pdf"  # type: ignore
        await s3.download_file(bucket, filename, temp_filename)
    return Path(temp_filename)


async def send_to_s3(file, filepath_destination):
    """
    Отправка файла в S3 хранилище
    :param file: исходный файл
    :param filepath_destination: имя файла в S3
    :return: s3_path: путь до файла в S3
    """
    s3_path = await upload(filepath_destination, Path(file), bucket=BUCKET_NAME_S3)
    return s3_path


async def send_then_delete_file(id_zakaz, pdf_path, directory="labels"):
    logger.info(f"Отправляем файл {pdf_path} в хранилище S3 id_zakaz={id_zakaz}")
    s3_path = await send_to_s3(
        pdf_path, f"{directory}/{pdf_path.split('/')[-1].replace(' ', '_')}"
    )
    # удаление файла
    Path(pdf_path).unlink()
    logger.info(
        f"Файл {pdf_path} успешно отправлен в хранилище S3 и находится по пути {s3_path} id_zakaz={id_zakaz}"
    )
    return s3_path


@lru_cache(maxsize=1)
def get_session():
    return aioboto3.Session()


async def upload(
    destination_filepath: str,
    file: Path,
    bucket: str,
) -> str:
    """
    destination_filepath - итоговое имя файла на s3

    bucket - имя бакета
    """
    session = get_session()
    async with session.client(
        "s3",
        aws_access_key_id=SETTINGS.aws_access_key_id,
        aws_secret_access_key=SETTINGS.aws_secret_access_key,
        endpoint_url=SETTINGS.ENDPOINT_S3,
    ) as s3:
        try:
            with file.open("rb") as spfp:
                logger.info(f"Uploading {destination_filepath} to s3 bucket: {bucket}")
                await s3.upload_fileobj(spfp, bucket, destination_filepath)
                logger.info(
                    f"Finished Uploading {destination_filepath} to s3 bucket: {bucket}"
                )
        except Exception as e:
            logger.exception(
                f"Unable to s3 upload file to {destination_filepath}: {e} ({type(e)})"
            )
            raise ValueError(
                "Не удалось загрузить файл в S3. "
                "Обратитесь с данной ошибкой к разработчикам."
            )

    return destination_filepath
