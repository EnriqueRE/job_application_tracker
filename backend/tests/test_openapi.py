import json
from pathlib import Path

from tracker.openapi import main


def test_dumps_openapi_schema_without_a_running_server(tmp_path: Path) -> None:
    out = tmp_path / "openapi.json"

    main([str(out)])

    schema = json.loads(out.read_text())
    health = schema["paths"]["/api/health"]["get"]
    ok_schema = health["responses"]["200"]["content"]["application/json"]["schema"]
    assert ok_schema == {"$ref": "#/components/schemas/HealthStatus"}
    assert set(schema["components"]["schemas"]["HealthStatus"]["properties"]) == {
        "status",
        "database",
    }
