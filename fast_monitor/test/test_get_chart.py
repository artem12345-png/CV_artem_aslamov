from io import BytesIO
from PIL import Image


def test_get_chart(client):
    response = client.get("/get_chart")

    assert response.status_code == 200
    chart = Image.open(BytesIO(response.content))
    assert chart.size == (1800, 600)
