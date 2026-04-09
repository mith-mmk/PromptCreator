import argparse
import json
import os
import re
import sqlite3


def strip_jsonl_comments(all_text):
    all_text = re.sub(r"/\*.*?\*/", "", all_text, flags=re.DOTALL)
    lines = all_text.split("\n")
    stripped = []
    for item in lines:
        item = re.sub(r"\s*\/\/.*$", "", item)
        if re.match(r"^\s*$", item):
            continue
        stripped.append(item)
    return stripped


def encode_json_field(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def normalize_jsonl_item(item, default_weight=0.1):
    normalized = dict(item)
    weight = normalized.pop(
        "W", normalized.pop("weight", normalized.pop("weigth", default_weight))
    )
    category = normalized.pop("C", normalized.pop("category", ["*"]))
    variable = normalized.pop(
        "V", normalized.pop("variable", normalized.pop("variables", [""]))
    )
    name = normalized.pop("name", normalized.pop("title", ""))

    if name == "":
        if isinstance(variable, list) and len(variable) > 0:
            name = str(variable[0])
        elif variable is not None:
            name = str(variable)

    return {
        "name": str(name),
        "category": encode_json_field(category),
        "weight": float(weight),
        "variable": encode_json_field(variable),
        "attributes": json.dumps(normalized, ensure_ascii=False),
        "attributes_dict": normalized,
    }


def is_expandable_column_name(name):
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) is not None


def ensure_expanded_columns(conn, table, records):
    existing_columns = {
        row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    }
    expanded_columns = set()
    for record in records:
        for key in record["attributes_dict"].keys():
            if is_expandable_column_name(key):
                expanded_columns.add(key)
    for column in sorted(expanded_columns):
        if column not in existing_columns:
            conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" TEXT')


def load_jsonl_records(filename):
    with open(filename, "r", encoding="utf_8") as f:
        lines = strip_jsonl_comments(f.read())
    records = []
    for idx, line in enumerate(lines, start=1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error {filename} line{idx}: {e}") from e
        if item is None:
            continue
        if not isinstance(item, dict):
            raise ValueError(f"jsonl record must be object {filename} line{idx}")
        records.append(normalize_jsonl_item(item))
    return records


def import_jsonl_to_db(
    filename, db_connection, table=None, truncate=False, name="default"
):
    if table is None:
        table = os.path.splitext(os.path.basename(filename))[0]

    records = load_jsonl_records(filename)
    conn = sqlite3.connect(db_connection)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{table}" (
                __name__ TEXT,
                category TEXT,
                weight REAL,
                variable TEXT,
                attributes TEXT
            )
            """
        )
        ensure_expanded_columns(conn, table, records)
        if truncate:
            conn.execute(f'DELETE FROM "{table}"')
        expanded_columns = [
            row[1]
            for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            if row[1]
            not in {"__name__", "category", "weight", "variable", "attributes"}
        ]
        insert_columns = [
            "__name__",
            "category",
            "weight",
            "variable",
            "attributes",
            *expanded_columns,
        ]
        quoted_columns = ", ".join([f'"{column}"' for column in insert_columns])
        placeholders = ", ".join(["?"] * len(insert_columns))
        conn.executemany(
            f'INSERT INTO "{table}" ({quoted_columns}) VALUES ({placeholders})',
            [
                (
                    name,
                    record["category"],
                    record["weight"],
                    record["variable"],
                    record["attributes"],
                    *[
                        encode_json_field(record["attributes_dict"].get(column))
                        for column in expanded_columns
                    ],
                )
                for record in records
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return len(records)


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="input jsonl file")
    parser.add_argument("db", type=str, help="sqlite3 database file")
    parser.add_argument(
        "table",
        type=str,
        nargs="?",
        default=None,
        help="destination table name, default is input file stem",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="default",
        help="name to store in __name__ column, default is 'default'",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="delete existing rows in the destination table before import",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    count = import_jsonl_to_db(
        args.input, args.db, args.table, args.truncate, args.name
    )
    print(f"imported {count} rows")


if __name__ == "__main__":
    main()
