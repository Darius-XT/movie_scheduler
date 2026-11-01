import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from movie_scheduler.core.exceptions import register_exception_handlers
from movie_scheduler.features.backup.repository import BackupWriteData, backup_repository
from movie_scheduler.features.backup.router import router


@pytest.fixture
def client(sample_records: BackupWriteData) -> TestClient:
    backup_repository.replace_all(sample_records)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_download_and_restore(client: TestClient) -> None:
    response = client.get("/api/backups/export")
    assert response.status_code == 200
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    backup = response.json()
    assert backup["success"] is True
    assert set(backup["data"]) == {
        "application",
        "format_version",
        "exported_at",
        "cinemas",
        "movies",
        "movie_shows",
        "planning_items",
    }
    result = client.post("/api/backups/import", json={"backup": backup, "confirm_replace": True})
    assert result.status_code == 200
    assert result.json() == {
        "success": True,
        "data": {"cinemas": 1, "movies": 2, "movie_shows": 1, "planning_items": 1},
    }


@pytest.mark.parametrize(
    "problem",
    [
        "version",
        "application",
        "missing_table",
        "missing_field",
        "unknown_field",
        "boolean",
        "channel",
        "location",
        "timestamp",
        "confirmation",
        "duplicate",
        "failed_export",
    ],
)
def test_reject_invalid_upload_without_changes(client: TestClient, problem: str) -> None:
    backup = client.get("/api/backups/export").json()
    request = {"backup": backup, "confirm_replace": True}
    if problem == "version":
        backup["data"]["format_version"] = 99
    elif problem == "application":
        backup["data"]["application"] = "other"
    elif problem == "missing_table":
        del backup["data"]["movies"]
    elif problem == "missing_field":
        del backup["data"]["movies"][0]["updated_at"]
    elif problem == "unknown_field":
        backup["data"]["cookie"] = "must not import"
    elif problem == "boolean":
        backup["data"]["movies"][0]["is_wished"] = "false"
    elif problem == "channel":
        backup["data"]["movies"][0]["channels"] = ["unknown"]
    elif problem == "location":
        backup["data"]["movies"][0]["viewing_location"] = "other"
    elif problem == "timestamp":
        backup["data"]["movies"][0]["updated_at"] = "invalid"
    elif problem == "confirmation":
        request["confirm_replace"] = False
    elif problem == "duplicate":
        backup["data"]["movies"].append(backup["data"]["movies"][0])
    else:
        backup["success"] = False
    response = client.post("/api/backups/import", json=request)
    assert response.status_code in {400, 422}
    assert response.json()["success"] is False
    assert isinstance(response.json()["error"], str)
    assert len(client.get("/api/backups/export").json()["data"]["movies"]) == 2


def test_empty_backup_requires_confirmation_and_clears_tables(client: TestClient) -> None:
    backup = client.get("/api/backups/export").json()
    for name in ("cinemas", "movies", "movie_shows", "planning_items"):
        backup["data"][name] = []
    assert client.post("/api/backups/import", json={"backup": backup}).status_code == 422
    response = client.post("/api/backups/import", json={"backup": backup, "confirm_replace": True})
    assert response.status_code == 200
    assert all(count == 0 for count in response.json()["data"].values())


def test_malformed_json_uses_error_envelope(client: TestClient) -> None:
    response = client.post("/api/backups/import", content="{bad", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["success"] is False
