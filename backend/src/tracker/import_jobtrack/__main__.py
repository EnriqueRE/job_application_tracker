"""Import a JobTrack database and its Job Description files into Postgres.

    uv run python -m tracker.import_jobtrack \\
        --sqlite /path/to/jobtrack.db \\
        --markdown-dir /path/to/job_applications \\
        --report import-report.json

The target database (``--database-url``, default ``DATABASE_URL``) must already be migrated.
Everything runs in one transaction, and the report is written before it commits: on any
error (including failing to write the report) Postgres is left unchanged.
Re-running is safe; rows imported before are skipped.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tracker.import_jobtrack.importer import import_jobtrack
from tracker.settings import get_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tracker.import_jobtrack",
        description="Import a JobTrack SQLite database and its Markdown Job Descriptions.",
    )
    parser.add_argument("--sqlite", type=Path, required=True, help="JobTrack's jobtrack.db")
    parser.add_argument(
        "--markdown-dir", type=Path, required=True, help="JobTrack's job_applications directory"
    )
    parser.add_argument("--report", type=Path, required=True, help="where to write the JSON report")
    parser.add_argument("--database-url", help="target Postgres URL (default: DATABASE_URL)")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    engine = create_engine(args.database_url or get_settings().database_url)
    try:
        with Session(engine) as session, session.begin():
            report = import_jobtrack(
                session, sqlite_path=args.sqlite, markdown_dir=args.markdown_dir
            )
            args.report.write_text(
                json.dumps(report.to_json(), indent=2, ensure_ascii=False) + "\n"
            )
    finally:
        engine.dispose()
    for entity, counts in report.counts.items():
        print(
            f"{entity}: {counts.source} in JobTrack, {counts.created} created, "
            f"{counts.already_imported} already imported, {counts.reused_existing} reused"
        )
    print(
        f"job descriptions: {len(report.matched_files)} files matched, "
        f"{len(report.unmatched_files)} unmatched, "
        f"{len(report.applications_without_job_description)} applications without one"
    )
    print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
