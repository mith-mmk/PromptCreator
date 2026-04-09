import sqlite3
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

from modules.reader import read_file_v2

_JSONL2DB_PATH = Path(__file__).resolve().parents[1] / "tools" / "jsonl2db.py"
_JSONL2DB_SPEC = spec_from_file_location("test_jsonl2db", _JSONL2DB_PATH)
assert _JSONL2DB_SPEC is not None
assert _JSONL2DB_SPEC.loader is not None
_JSONL2DB_MODULE = module_from_spec(_JSONL2DB_SPEC)
_JSONL2DB_SPEC.loader.exec_module(_JSONL2DB_MODULE)
import_jsonl_to_db = _JSONL2DB_MODULE.import_jsonl_to_db


def make_test_dir(name):
    path = Path(__file__).resolve().parents[1] / ".codex-tmp" / f"{name}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_read_file_v2_reads_sqlite_rows_with_schema():
    test_dir = make_test_dir("test_reader_db_schema")
    db_file = test_dir / "items.sqlite3"
    conn = sqlite3.connect(db_file)
    try:
        conn.execute(
            """
            CREATE TABLE date_items (
                name TEXT,
                category TEXT,
                weight REAL,
                variable TEXT,
                attributes TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO date_items (name, category, weight, variable, attributes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "day-animal",
                '["animal","animal-xl"]',
                0.2,
                '["day","sunny"]',
                '{"animal":"cat","size":"small"}',
            ),
        )
        conn.execute(
            """
            INSERT INTO date_items (name, category, weight, variable, attributes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "night-human",
                '["human"]',
                0.4,
                '"night"',
                '{"animal":"human","size":"large"}',
            ),
        )
        conn.commit()
    finally:
        conn.close()

    records = read_file_v2(
        "date_items[category = `animal` and animal = `cat`]",
        database={"db": "sqlite3", "db_connection": str(db_file)},
    )

    assert len(records) == 1
    assert records[0]["variables"] == ["day", "sunny"]
    assert records[0]["weight"] == 0.2
    assert records[0]["animal"] == "cat"
    assert records[0]["name"] == "day-animal"
    assert records[0]["query"] == "animal"


def test_jsonl2db_import_creates_readable_rows():
    test_dir = make_test_dir("test_jsonl2db_import")
    jsonl_file = test_dir / "sample.jsonl"
    jsonl_file.write_text(
        "\n".join(
            [
                '{"W": 0.1, "C": ["animal"], "V": "day", "animal": "cat", "title": "Day Cat"}',
                '{"W": 0.3, "C": ["human"], "V": ["night", "city"], "animal": "human"}',
            ]
        ),
        encoding="utf-8",
    )
    db_file = test_dir / "import.sqlite3"

    count = import_jsonl_to_db(str(jsonl_file), str(db_file), "date_items")

    assert count == 2

    records = read_file_v2(
        "date_items[category = `animal`]",
        database={"db": "sqlite3", "db_connection": str(db_file)},
    )

    assert len(records) == 1
    assert records[0]["variables"] == ["day"]
    assert records[0]["animal"] == "cat"
    assert records[0]["name"] == "Day Cat"

    conn = sqlite3.connect(db_file)
    try:
        columns = {
            row[1] for row in conn.execute('PRAGMA table_info("date_items")').fetchall()
        }
    finally:
        conn.close()

    assert "animal" in columns
