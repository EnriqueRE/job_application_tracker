"""The built SPA is served from the same origin as ``/api``."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tracker.app import create_app

INDEX_HTML = "<!doctype html><title>Tracker SPA</title>"


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text(INDEX_HTML)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    return tmp_path


@pytest.fixture
def spa_client(static_dir: Path) -> TestClient:
    return TestClient(create_app(static_dir=static_dir))


def test_root_serves_index_html(spa_client: TestClient) -> None:
    response = spa_client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX_HTML


def test_serves_built_asset_files(spa_client: TestClient) -> None:
    response = spa_client.get("/assets/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert response.text == "console.log('app')"


def test_client_side_routes_fall_back_to_index_html(spa_client: TestClient) -> None:
    response = spa_client.get("/applications/42/edit")

    assert response.status_code == 200
    assert response.text == INDEX_HTML


@pytest.mark.parametrize("path", ["/api", "/api/", "/api/nope", "/api/applications/42"])
def test_unknown_api_paths_are_404_not_index_html(spa_client: TestClient, path: str) -> None:
    response = spa_client.get(path)

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"detail": "Not Found"}


def test_api_routes_take_precedence_over_the_spa(spa_client: TestClient) -> None:
    response = spa_client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]


def test_files_outside_the_static_dir_are_not_served(tmp_path: Path) -> None:
    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(INDEX_HTML)
    (tmp_path / "secret.txt").write_text("secret")
    client = TestClient(create_app(static_dir=static_dir))

    response = client.get("/%2E%2E/secret.txt")

    assert "secret" not in response.text


def test_static_dir_is_read_from_the_environment(
    static_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STATIC_DIR", str(static_dir))

    response = TestClient(create_app()).get("/organizations")

    assert response.text == INDEX_HTML


def test_without_a_static_dir_only_the_api_is_served(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STATIC_DIR", raising=False)

    response = TestClient(create_app()).get("/")

    assert response.status_code == 404
