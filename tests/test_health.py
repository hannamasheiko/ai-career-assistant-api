from unittest.mock import AsyncMock

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "ok"
    assert "environment" in response_data


def test_db_health_check(client):
    response = client.get("/db-health")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


def test_db_health_check_returns_503_when_database_unreachable(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        AsyncSession,
        "execute",
        AsyncMock(
            side_effect=OperationalError(
                "SELECT 1",
                None,
                Exception("connection refused"),
            )
        ),
    )

    response = client.get("/db-health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unreachable."}
