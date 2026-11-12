"""Guards the isolation promise of the ``db_session`` fixture.

The two tests run in file order: the first commits a row, the second checks
that the row (and even the table) was rolled back.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def test_committed_writes_are_visible_within_the_same_test(db_session: Session) -> None:
    db_session.execute(text("CREATE TABLE harness_probe (id int PRIMARY KEY)"))
    db_session.execute(text("INSERT INTO harness_probe (id) VALUES (1)"))
    db_session.commit()

    assert db_session.execute(text("SELECT count(*) FROM harness_probe")).scalar_one() == 1


def test_writes_from_a_previous_test_are_rolled_back(db_session: Session) -> None:
    exists = db_session.execute(
        text("SELECT to_regclass('harness_probe') IS NOT NULL")
    ).scalar_one()

    assert exists is False


def test_migrations_have_run(db_session: Session) -> None:
    exists = db_session.execute(
        text("SELECT to_regclass('alembic_version') IS NOT NULL")
    ).scalar_one()

    assert exists is True
