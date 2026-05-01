def test_lookup_returns_manual_when_not_configured(client, auth_headers, monkeypatch):
    monkeypatch.delenv("MITCHELL1_API_KEY", raising=False)
    resp = client.post(
        "/labor-lookup",
        json={"year": 2020, "make": "Ford", "model": "F-150", "service": "Oil Change"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["source"] == "manual"
    assert resp.json()["hours"] is None


def test_lookup_returns_hours_from_api(client, auth_headers, monkeypatch):
    monkeypatch.setenv("MITCHELL1_API_KEY", "fake-key")
    from unittest.mock import AsyncMock, patch, MagicMock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"laborHours": 0.5}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = client.post(
            "/labor-lookup",
            json={"year": 2020, "make": "Ford", "model": "F-150", "service": "Oil Change"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["hours"] == 0.5
    assert resp.json()["source"] == "mitchell1"


def test_lookup_falls_back_to_manual_on_api_error(client, auth_headers, monkeypatch):
    monkeypatch.setenv("MITCHELL1_API_KEY", "fake-key")
    from unittest.mock import AsyncMock, patch
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = client.post(
            "/labor-lookup",
            json={"year": 2020, "make": "Ford", "model": "F-150", "service": "Oil Change"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["source"] == "manual"
    assert resp.json()["hours"] is None
