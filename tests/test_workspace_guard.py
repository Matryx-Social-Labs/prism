"""The suite runs only on a database whose name ends in _test (tests/conftest.py)."""

from tests.conftest import database_refusal


def test_refuses_the_shared_local_dev_database() -> None:
    assert database_refusal("postgresql+asyncpg://prism:prism@localhost:5432/prism")


def test_refuses_a_production_host_without_the_test_suffix() -> None:
    assert database_refusal("postgresql+asyncpg://u:p@proxy.rlwy.net:41234/railway")


def test_accepts_a_workspace_test_database() -> None:
    assert database_refusal("postgresql+asyncpg://prism:prism@localhost:5432/prism_port_au_prince_test") is None


def test_accepts_the_ci_test_database() -> None:
    assert database_refusal("postgresql+asyncpg://prism:prism@localhost:5432/prism_test") is None
