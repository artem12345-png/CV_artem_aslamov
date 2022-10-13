import datetime
from io import BytesIO

import fitz

from env import PLACEMARKET
from wb.consts import DIRECTORY


def concat_pdf(pdfs: list[BytesIO], order_id=None, is_act=False) -> str:
    """
    Соединяет PDFки в одну большую PDF
    :return: путь до файла
    """
    doc = fitz.open()
    for p in pdfs:
        candidate = fitz.Document(stream=p)
        doc.insert_pdf(candidate)
    if order_id:
        filename = (
            f"{DIRECTORY}/{order_id}_{PLACEMARKET}_{str(datetime.date.today())}.pdf"
        )
    else:
        filename = f"{DIRECTORY}/{PLACEMARKET}{'_act' if is_act else ''}_{str(datetime.date.today())}.pdf"
    doc.save(filename)

    return filename
