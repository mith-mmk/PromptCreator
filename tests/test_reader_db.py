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
                __name__ TEXT,
                category TEXT,
                weight REAL,
                variable TEXT,
                attributes TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO date_items (__name__, category, weight, variable, attributes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "date_source",
                '["animal","animal-xl"]',
                0.2,
                '["day","sunny"]',
                '{"animal":"cat","size":"small"}',
            ),
        )
        conn.execute(
            """
            INSERT INTO date_items (__name__, category, weight, variable, attributes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "date_source",
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
        "date_items[__name__ = `date_source` and category = `animal` and animal = `cat`]",
        database={"db": "sqlite3", "db_connection": str(db_file)},
    )

    assert len(records) == 1
    assert records[0]["variables"] == ["day", "sunny"]
    assert records[0]["weight"] == 0.2
    assert records[0]["animal"] == "cat"
    assert records[0]["__name__"] == "date_source"
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
        "date_items[__name__ = `sample` and category = `animal`]",
        database={"db": "sqlite3", "db_connection": str(db_file)},
    )

    assert len(records) == 1
    assert records[0]["variables"] == ["day"]
    assert records[0]["animal"] == "cat"
    assert records[0]["__name__"] == "sample"
    assert records[0]["title"] == "Day Cat"

    conn = sqlite3.connect(db_file)
    try:
        columns = {
            row[1] for row in conn.execute('PRAGMA table_info("date_items")').fetchall()
        }
    finally:
        conn.close()

    assert "animal" in columns


def test_jsonl2db_import_recursively_loads_directory():
    test_dir = make_test_dir("test_jsonl2db_recursive")
    root_dir = test_dir / "jsonl"
    (root_dir / "animals").mkdir(parents=True, exist_ok=True)
    (root_dir / "humans").mkdir(parents=True, exist_ok=True)

    (root_dir / "animals" / "eyes.jsonl").write_text(
        '{"W": 0.1, "C": ["animal"], "V": "blue eyes", "kind": "cat"}\n',
        encoding="utf-8",
    )
    (root_dir / "humans" / "eyes.jsonl").write_text(
        '{"W": 0.2, "C": ["human"], "V": "green eyes", "kind": "person"}\n',
        encoding="utf-8",
    )

    db_file = test_dir / "recursive.sqlite3"
    count = import_jsonl_to_db(str(root_dir), str(db_file), "jsonl_items")

    assert count == 2

    animal_records = read_file_v2(
        "jsonl_items[__name__ = `animals__eyes` and category = `animal`]",
        database={"db": "sqlite3", "db_connection": str(db_file)},
    )
    human_records = read_file_v2(
        "jsonl_items[__name__ = `humans__eyes` and category = `human`]",
        database={"db": "sqlite3", "db_connection": str(db_file)},
    )

    assert len(animal_records) == 1
    assert animal_records[0]["kind"] == "cat"
    assert animal_records[0]["__name__"] == "animals__eyes"

    assert len(human_records) == 1
    assert human_records[0]["kind"] == "person"
    assert human_records[0]["__name__"] == "humans__eyes"
