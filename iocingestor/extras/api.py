import sqlite3
from pathlib import Path
from typing import Generator, List, Optional

from environs import Env
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from iocingestor.schemas import Artifact

env = Env()
env.read_env()

DATABASE = env.str("IOCINGESTOR_SQLITE3_DATABASE", "artifacts.db")

CURRENT_DIR = Path(__file__).parent.absolute()

router = APIRouter()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    try:
        db = sqlite3.connect(DATABASE)
        yield db
    finally:
        db.close()


def get_tables(db: sqlite3.Connection) -> List[str]:
    cursor = db.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    return [str(e[0]) for e in cursor.fetchall()]


def get_artifacts(
    db: sqlite3.Connection, table: str, limit: int = 100, offset: int = 0
) -> List[Artifact]:
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (limit, offset))

    artifacts: List[Artifact] = []
    columns = [c[0] for c in cursor.description]
    for row in cursor.fetchall():
        artifacts.append(Artifact.parse_obj({k: v for k, v in zip(columns, row)}))

    return artifacts


def read_html(filename: str = "index.html", current_dir: Path = CURRENT_DIR) -> str:
    path = current_dir / f"public/{filename}"
    with open(path) as f:
        return f.read()


@router.get(
    "/api/tables", response_model=List[str],
)
def tables(db: sqlite3.Connection = Depends(get_db)):
    return get_tables(db)


@router.get(
    "/api/tables/{table}", response_model=List[Artifact],
)
def artifacts(
    table: str,
    limit: int = 100,
    offset: int = 0,
    db: sqlite3.Connection = Depends(get_db),
):
    tables = get_tables(db)
    if table in tables:
        return get_artifacts(db, table, limit, offset)

    raise HTTPException(status_code=404, detail=f"No table: {table}")


@router.get("/", response_class=HTMLResponse)
def index_html():
    return read_html("index.html")


@router.get("/{table}", response_class=HTMLResponse)
def table_html(table: Optional[str] = None):
    if table:
        return read_html("list.html")
    else:
        return read_html("index.html")
