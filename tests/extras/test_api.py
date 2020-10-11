import sqlite3

import pytest

from iocingestor.extras.api import get_artifacts, get_tables


@pytest.mark.parametrize(
    "table,expected",
    [("domain", 10), ("hash", 0), ("ipaddress", 0), ("task", 0), ("url", 0),],
)
def test_get_artifacts(database: sqlite3.Connection, table: str, expected: int):
    assert len(get_artifacts(database, table)) == expected


def test_get_artifacts_with_domain(database: sqlite3.Connection):
    artifacts = get_artifacts(database, "domain")
    for i in range(10):
        assert artifacts[i].artifact == f"{i}.example.com"
        assert artifacts[i].reference_link == ""
        assert artifacts[i].reference_text == ""
        assert artifacts[i].created_date != ""


@pytest.mark.parametrize(
    "limit,offset,expected",
    [(10, 0, 10), (5, 0, 5), (10, 5, 5), (10, 1, 9), (0, 1, 0),],
)
def test_get_artifacts_with_limit_and_offset(
    database: sqlite3.Connection, limit: int, offset: int, expected: int
):
    artifacts = get_artifacts(database, "domain", limit=limit, offset=offset)
    assert len(artifacts) == expected


def test_get_table(database: sqlite3.Connection):
    assert len(get_tables(database)) == 5
