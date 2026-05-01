import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.main import app


def test_diagnose_analyze_returns_results(client, auth_headers, mock_db):
    fake_carmd = {
        "data": [
            {
                "urgency": 1,
                "urgency_desc": "Critical",
                "desc": "Misfire in cylinder 2",
                "layman_desc": "Engine is misfiring",
                "part": "Ignition Coil",
                "repair": {"difficulty": "Moderate"},
            }
        ]
    }
    with patch("src.api.diagnose._carmd_post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_carmd
        with patch("src.api.diagnose._get_carmd_creds", new_callable=AsyncMock, return_value=("key", "token")):
            resp = client.post(
                "/diagnose/analyze",
                json={"year": 2019, "make": "Toyota", "model": "Camry", "dtcs": ["P0300"]},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    body = resp.json()
    assert "diagnosis" in body
    assert body["diagnosis"][0]["desc"] == "Misfire in cylinder 2"


def test_diagnose_recalls_returns_list(client, auth_headers, mock_db):
    fake_recalls = {"data": [{"recall_date": "2020-01-01", "component": "Brakes", "consequence": "Loss of braking"}]}
    with patch("src.api.diagnose._carmd_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_recalls
        with patch("src.api.diagnose._get_carmd_creds", new_callable=AsyncMock, return_value=("key", "token")):
            resp = client.get(
                "/diagnose/recalls",
                params={"year": 2019, "make": "Toyota", "model": "Camry"},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    assert len(resp.json()["recalls"]) == 1


def test_diagnose_no_credentials_raises_422(client, auth_headers, mock_db):
    with patch("src.api.diagnose._get_carmd_creds", new_callable=AsyncMock, return_value=(None, None)):
        resp = client.post(
            "/diagnose/analyze",
            json={"year": 2019, "make": "Toyota", "model": "Camry", "dtcs": ["P0300"]},
            headers=auth_headers,
        )
    assert resp.status_code == 422
