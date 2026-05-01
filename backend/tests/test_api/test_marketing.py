import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    import jwt, os
    token = jwt.encode(
        {"sub": "test-user-id", "shop_id": "test-shop-id"},
        os.environ.get("SECRET_KEY", "test-secret"),
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


def test_list_campaigns_empty(client, auth_headers):
    from unittest.mock import AsyncMock, MagicMock
    from src.db.base import get_db as real_get_db

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def override_db():
        yield mock_session

    app.dependency_overrides[real_get_db] = override_db
    try:
        resp = client.get("/marketing/campaigns", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(real_get_db, None)

    assert resp.status_code == 200
    assert resp.json() == []
