
from sqlalchemy import inspect

from backend.app.database import engine


def inspect_database():
    print("DATABASE:", engine.url.database)

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("TOTAL TABLES:", len(tables))

    for table_name in tables:
        print("\n" + "=" * 70)
        print("TABLE:", table_name)
        print("=" * 70)

        columns = inspector.get_columns(table_name)

        print("\nCOLUMNS:")

        for column in columns:
            print(
                "  Name:", column["name"],
                "| Type:", column["type"],
                "| Nullable:", column["nullable"],
                "| Primary key:", column.get("primary_key", False)
            )

        foreign_keys = inspector.get_foreign_keys(table_name)

        print("\nFOREIGN KEYS:")

        if not foreign_keys:
            print("  None")
        else:
            for fk in foreign_keys:
                print(
                    "  ",
                    fk["constrained_columns"],
                    "->",
                    fk["referred_table"],
                    fk["referred_columns"]
                )


if __name__ == "__main__":
    inspect_database()
