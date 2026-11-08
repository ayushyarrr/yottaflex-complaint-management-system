
import csv
import json
import sqlite3
from pathlib import Path

from sqlalchemy import MetaData, Table, select

from backend.app.database import engine


from decimal import Decimal


def json_value(value):
    """Convert database values into JSON-compatible values."""
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    if hasattr(value, "isoformat"):
        return value.isoformat()

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return value


def export_database():
    if engine.dialect.name != "sqlite":
        raise RuntimeError("This export script currently supports SQLite only.")

    database_path = engine.url.database

    if not database_path:
        raise RuntimeError("Could not determine the active SQLite database path.")

    database_file = Path(database_path)

    if not database_file.is_absolute():
        database_file = Path.cwd() / database_file

    if not database_file.exists():
        raise FileNotFoundError(
            f"Database not found: {database_file}"
        )

    output_dir = Path("data/generated/full")
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = MetaData()
    metadata.reflect(bind=engine)

    table_summaries = []

    with engine.connect() as connection:
        for table_name in sorted(metadata.tables):
            table = metadata.tables[table_name]

            result = connection.execute(select(table))
            rows = [dict(row._mapping) for row in result]

            json_rows = [
                {
                    key: json_value(value)
                    for key, value in row.items()
                }
                for row in rows
            ]

            # Export JSON
            json_path = output_dir / f"{table_name}.json"

            with json_path.open("w", encoding="utf-8") as file:
                json.dump(
                    json_rows,
                    file,
                    indent=2,
                    ensure_ascii=False
                )

            # Export CSV
            csv_path = output_dir / f"{table_name}.csv"

            with csv_path.open(
                "w",
                encoding="utf-8-sig",
                newline=""
            ) as file:
                if table.columns:
                    writer = csv.DictWriter(
                        file,
                        fieldnames=list(table.columns.keys())
                    )
                    writer.writeheader()

                    for row in json_rows:
                        writer.writerow({
                            key: (
                                json.dumps(value, ensure_ascii=False)
                                if isinstance(value, (dict, list))
                                else value
                            )
                            for key, value in row.items()
                        })

            table_summaries.append({
                "table": table_name,
                "records": len(rows),
                "csv_file": csv_path.name,
                "json_file": json_path.name
            })

            print(f"Exported {table_name}: {len(rows)} records")

    # Export a complete SQLite SQL dump
    sql_path = output_dir / "full_database.sql"

    with sqlite3.connect(str(database_file)) as source:
        with sql_path.open("w", encoding="utf-8") as file:
            for statement in source.iterdump():
                file.write(statement + "\n")

    # Export a manifest describing the generated files
    manifest = {
        "database": database_file.name,
        "export_directory": str(output_dir),
        "format": ["CSV", "JSON", "SQL"],
        "tables": table_summaries,
        "total_tables": len(table_summaries),
        "total_records": sum(
            item["records"] for item in table_summaries
        )
    }

    manifest_path = output_dir / "export_manifest.json"

    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    print("\nExport completed successfully.")
    print(f"Database: {database_file}")
    print(f"Output directory: {output_dir}")
    print(f"Tables exported: {manifest['total_tables']}")
    print(f"Total records exported: {manifest['total_records']}")
    print(f"SQL dump: {sql_path}")


if __name__ == "__main__":
    export_database()
