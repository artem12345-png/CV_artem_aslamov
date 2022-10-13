def test_self_check(client):
    response = client.get("/self_check")

    assert response.status_code == 200
    assert response.json() == {"status": "Ok"}
