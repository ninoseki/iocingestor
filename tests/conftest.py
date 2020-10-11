import sqlite3
from typing import Generator

import pytest
from environs import Env

from iocingestor.artifacts import Domain
from iocingestor.operators.sqlite import Plugin

env = Env()
env.read_env()


@pytest.fixture()
def database() -> Generator[sqlite3.Connection, None, None]:
    filename = env.str("IOCINGESTOR_SQLITE3_DATABASE", ":memory:")

    plugin = Plugin(filename)

    for i in range(10):
        plugin._insert_artifact(
            Domain(artifact=f"{i}.example.com", source_name="Dummy")
        )

    yield plugin.sql

    plugin.sql.close()
