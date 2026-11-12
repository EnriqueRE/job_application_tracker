"""Write the API's OpenAPI schema to a file without starting a server.

Used by the frontend's `npm run gen:api` to regenerate its TypeScript client:

    uv run python -m tracker.openapi ../frontend/openapi.json
"""

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from tracker.app import create_app


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: python -m tracker.openapi OUTPUT.json")
    schema = create_app().openapi()
    Path(args[0]).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
