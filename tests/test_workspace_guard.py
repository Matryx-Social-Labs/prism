"""The suite runs only on a database whose name ends in _test (tests/conftest.py)."""

import os
import subprocess
import sys

import pytest

from scripts.fresh_test_db import refusal as drop_refusal
from tests.conftest import database_refusal

LOCAL = "postgresql+asyncpg://prism:prism@localhost:5432"


@pytest.mark.parametrize(
    "url",
    [
        f"{LOCAL}/prism",  # the shared dev database: a local host is not enough
        "postgresql+asyncpg://u:p@proxy.rlwy.net:41234/railway",
        f"{LOCAL}/prism_test_backup",
        f"{LOCAL}/prism_latest",
        f"{LOCAL}/prism?application_name=x_test",
        "postgresql+asyncpg://u:p@db_test.example:5432/prism",
        f"{LOCAL}/prism_test?database=prism",  # the query names the database SQLAlchemy opens
        LOCAL,
    ],
)
def test_refuses_a_database_not_named_test(url: str) -> None:
    assert database_refusal(url)


@pytest.mark.parametrize(
    "url", [f"{LOCAL}/prism_port_au_prince_test", f"{LOCAL}/prism_test", f"{LOCAL}/prism_test?ssl=require"]
)
def test_accepts_a_test_database(url: str) -> None:
    assert database_refusal(url) is None


def test_the_session_exits_2_before_any_test_when_the_database_is_not_a_test_one() -> None:
    """The wiring, not the rule: TEST_DATABASE_URL reaches settings and the refusal stops the run."""
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", __file__, "-k", "accepts"],
        env={**os.environ, "TEST_DATABASE_URL": f"{LOCAL}/prism"},
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2, run.stdout + run.stderr
    assert "Refusing to run tests" in run.stdout + run.stderr


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://prism:prism@localhost:5432/prism",
        "postgresql://u:p@proxy.rlwy.net:41234/stage_test",  # a _test name on another host is still not ours to drop
        "postgresql://prism:prism@localhost:5432/prism_test?database=prism",
        'postgresql://prism:prism@localhost:5432/x"; DROP DATABASE prism; --_test',
        "",
    ],
)
def test_make_check_will_not_drop_anything_but_a_local_test_database(url: str) -> None:
    assert drop_refusal(url)


def test_make_check_may_recreate_a_local_test_database() -> None:
    assert drop_refusal("postgresql://prism:prism@localhost:5432/prism_port_au_prince_test") is None
