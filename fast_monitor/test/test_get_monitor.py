from io import BytesIO
from PIL import Image


def test_get_monitor(client):
    response = client.get("/get_monitor")

    assert response.status_code == 200
    image = Image.open(BytesIO(response.content))
    assert image.size == (1366, 768)
