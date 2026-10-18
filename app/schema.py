"""Small in-place upgrades for databases created by older versions of the app.

db.create_all() only creates missing tables; it never changes existing ones. Column renames made
during development therefore left older instance/placement.db files with the old column names.
"""
from sqlalchemy import inspect, text

# (table, old column, new column)
COLUMN_RENAMES = [
    ("sql_attempts", "query", "query_text"),
]


def upgrade_schema(engine):
    """Rename legacy columns in place (existing rows are kept). Returns the renames performed."""
    done = []
    inspector = inspect(engine)
    for table, old, new in COLUMN_RENAMES:
        if table not in inspector.get_table_names():
            continue
        columns = {c["name"] for c in inspector.get_columns(table)}
        if old in columns and new not in columns:
            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}"'))
            done.append((table, old, new))
    return done
