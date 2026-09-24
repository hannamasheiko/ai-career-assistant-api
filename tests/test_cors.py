def test_cors_allows_configured_origin(client):
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )


def test_cors_does_not_allow_unlisted_origin(client):
    response = client.get(
        "/health",
        headers={"Origin": "http://evil.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
