from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tracker.app import create_app
from tracker.db import get_session


def test_health_reports_ok_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_unavailable_when_database_is_unreachable() -> None:
    unreachable = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none",
        connect_args={"connect_timeout": 1},
    )

    def unreachable_session() -> Iterator[Session]:
        with Session(unreachable) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = unreachable_session
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unreachable"}
