"""The Compose ``backup`` service's script: dump the database, keep the newest N dumps.

The script is run for real with a stub ``pg_dump`` on ``PATH``, so these tests cover
the file handling and retention without a database. ``test_backup_restore.py`` covers
a real dump and restore.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "backup" / "backup.sh"

STUB_PG_DUMP = """#!/bin/sh
if [ -n "$STUB_PG_DUMP_FAIL" ]; then
    printf 'partial'
    echo 'pg_dump: connection refused' >&2
    exit 1
fi
printf 'dump args=%s' "$*"
"""


@pytest.fixture
def backup_dir(tmp_path: Path) -> Path:
    path = tmp_path / "backups"
    path.mkdir()
    return path


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / "bin"
    path.mkdir()
    pg_dump = path / "pg_dump"
    pg_dump.write_text(STUB_PG_DUMP)
    pg_dump.chmod(0o755)
    return path


def run_backup(backup_dir: Path, stub_bin: Path, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT)],
        env={
            "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
            "BACKUP_DIR": str(backup_dir),
            **env,
        },
        capture_output=True,
        text=True,
        check=False,
    )


def dumps(backup_dir: Path) -> list[str]:
    return sorted(p.name for p in backup_dir.iterdir())


def make_old_dumps(backup_dir: Path, count: int) -> list[str]:
    names = [f"tracker-202601{day:02d}T030000Z.dump" for day in range(1, count + 1)]
    for name in names:
        (backup_dir / name).write_text("old")
    return names


def test_writes_one_custom_format_dump(backup_dir: Path, stub_bin: Path) -> None:
    result = run_backup(backup_dir, stub_bin)

    assert result.returncode == 0, result.stderr
    [name] = dumps(backup_dir)
    assert name.startswith("tracker-")
    assert name.endswith(".dump")
    assert "--format=custom" in (backup_dir / name).read_text()


def test_keeps_the_14_most_recent_dumps_by_default(backup_dir: Path, stub_bin: Path) -> None:
    old = make_old_dumps(backup_dir, 20)

    result = run_backup(backup_dir, stub_bin)

    assert result.returncode == 0, result.stderr
    remaining = dumps(backup_dir)
    assert len(remaining) == 14
    # The new dump plus the 13 newest old ones survive.
    assert remaining[:13] == old[-13:]
    assert remaining[13] > old[-1]


def test_retention_count_is_configurable(backup_dir: Path, stub_bin: Path) -> None:
    old = make_old_dumps(backup_dir, 5)

    result = run_backup(backup_dir, stub_bin, BACKUP_KEEP="3")

    assert result.returncode == 0, result.stderr
    remaining = dumps(backup_dir)
    assert len(remaining) == 3
    assert remaining[:2] == old[-2:]


def test_retention_leaves_other_files_alone(backup_dir: Path, stub_bin: Path) -> None:
    make_old_dumps(backup_dir, 3)
    (backup_dir / "keep-me.txt").write_text("notes")
    (backup_dir / "manual.dump").write_text("hand-made")

    result = run_backup(backup_dir, stub_bin, BACKUP_KEEP="1")

    assert result.returncode == 0, result.stderr
    remaining = dumps(backup_dir)
    assert "keep-me.txt" in remaining
    assert "manual.dump" in remaining
    assert len([n for n in remaining if n.startswith("tracker-")]) == 1


def test_failed_dump_leaves_no_file_and_prunes_nothing(backup_dir: Path, stub_bin: Path) -> None:
    old = make_old_dumps(backup_dir, 3)

    result = run_backup(backup_dir, stub_bin, BACKUP_KEEP="1", STUB_PG_DUMP_FAIL="1")

    assert result.returncode != 0
    assert "connection refused" in result.stderr
    assert dumps(backup_dir) == old
