"""Safe, read-only SQL execution against a separate practice database.

Defence in depth (no single check is relied on):
  1. The practice DB is its own file, never the application database.
  2. It is opened read-only (mode=ro) with PRAGMA query_only = ON.
  3. A SQLite authorizer allows only SELECT/READ/recursive-CTE/safe functions;
     INSERT, UPDATE, DELETE, DROP, CREATE, ATTACH, PRAGMA, transactions etc. are denied.
  4. sqlite3 refuses multiple statements in one execute() call.
  5. Hard limits: SQL length, value size, expression depth, a wall-clock deadline
     enforced by a progress handler, and a cap on returned rows.
"""
import os
import sqlite3
import time
from pathlib import Path

MAX_SQL_LENGTH = 2000
TIME_LIMIT_SECONDS = 2.0
MAX_DISPLAY_ROWS = 100
MAX_CHECK_ROWS = 1000
PROGRESS_STEP = 10_000  # VM instructions between deadline checks

TABLES = ["students", "companies", "placements"]
BLOCKED_FUNCTIONS = {"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer"}

_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE}


class SqlLabError(Exception):
    """An error whose message is safe and helpful to show to the student."""


class QueryResult:
    def __init__(self, columns, rows, truncated):
        self.columns = columns
        self.rows = rows
        self.truncated = truncated


# ---------------------------------------------------------------- database
_SCHEMA = """
CREATE TABLE students (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, department TEXT NOT NULL,
    cgpa REAL NOT NULL, graduation_year INTEGER NOT NULL);
CREATE TABLE companies (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, sector TEXT NOT NULL);
CREATE TABLE placements (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    role TEXT NOT NULL, package_lpa REAL NOT NULL);
"""

_STUDENTS = [
    (1, "Aarav Mehta", "CSE", 8.9, 2025), (2, "Diya Nair", "CSE", 9.2, 2025),
    (3, "Kabir Singh", "ECE", 7.4, 2025), (4, "Meera Iyer", "ECE", 8.1, 2025),
    (5, "Rohan Das", "MECH", 6.8, 2025), (6, "Sana Khan", "CSE", 7.9, 2025),
    (7, "Vikram Rao", "MECH", 7.2, 2025), (8, "Ishita Paul", "IT", 8.6, 2025),
    (9, "Neil Joshi", "IT", 7.6, 2025), (10, "Tara Menon", "CSE", 9.5, 2025),
    (11, "Yash Patel", "ECE", 6.5, 2025), (12, "Zoya Ali", "IT", 8.3, 2025),
]
_COMPANIES = [
    (1, "Nimbus Tech", "IT Services"), (2, "Orbit Labs", "Product"),
    (3, "Quanta Systems", "Product"), (4, "Zenith Motors", "Manufacturing"),
    (5, "Helix Analytics", "Analytics"), (6, "Pioneer Bank", "Finance"),
]
_PLACEMENTS = [
    (1, 1, 2, "Software Engineer", 14.0), (2, 2, 2, "Software Engineer", 16.5),
    (3, 3, 4, "Graduate Engineer", 6.0), (4, 4, 3, "Embedded Engineer", 9.0),
    (5, 6, 1, "Systems Analyst", 6.5), (6, 8, 5, "Data Analyst", 8.5),
    (7, 9, 1, "Systems Analyst", 6.0), (8, 10, 3, "Software Engineer", 18.0),
    (9, 12, 5, "Data Analyst", 8.0), (10, 7, 4, "Graduate Engineer", 5.5),
]


def ensure_practice_db(path):
    """Create and seed the practice database if it does not exist yet."""
    if os.path.exists(path):
        return
    tmp_path = path + ".tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    conn = sqlite3.connect(tmp_path)
    try:
        conn.executescript(_SCHEMA)
        conn.executemany("INSERT INTO students VALUES (?,?,?,?,?)", _STUDENTS)
        conn.executemany("INSERT INTO companies VALUES (?,?,?)", _COMPANIES)
        conn.executemany("INSERT INTO placements VALUES (?,?,?,?,?)", _PLACEMENTS)
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp_path, path)


def _connect_readonly(path):
    uri = Path(os.path.abspath(path)).as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=1)
    conn.execute("PRAGMA query_only = ON")
    return conn


# ---------------------------------------------------------------- execution
def _authorizer(action, arg1, arg2, db_name, source):
    if action in _ALLOWED_ACTIONS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        # arg1 = table name; hide SQLite's internal tables
        if arg1 and arg1.lower().startswith("sqlite_"):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION:
        if arg2 and arg2.lower() in BLOCKED_FUNCTIONS:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _apply_limits(conn):
    limits = {
        "SQLITE_LIMIT_LENGTH": 100_000,          # max string/blob size
        "SQLITE_LIMIT_SQL_LENGTH": MAX_SQL_LENGTH,
        "SQLITE_LIMIT_COLUMN": 30,
        "SQLITE_LIMIT_EXPR_DEPTH": 50,
        "SQLITE_LIMIT_COMPOUND_SELECT": 10,
        "SQLITE_LIMIT_FUNCTION_ARG": 8,
        "SQLITE_LIMIT_LIKE_PATTERN_LENGTH": 200,
        "SQLITE_LIMIT_VARIABLE_NUMBER": 0,
        "SQLITE_LIMIT_ATTACHED": 0,
    }
    for name, value in limits.items():
        const = getattr(sqlite3, name, None)  # setlimit needs Python 3.11+
        if const is not None and hasattr(conn, "setlimit"):
            conn.setlimit(const, value)


def _friendly_error(exc, sql):
    msg = str(exc)
    low = msg.lower()
    if "not authorized" in low or "readonly" in low or "read-only" in low:
        return ("That statement isn't allowed. The SQL Lab only runs read-only SELECT "
                "queries on the practice tables.")
    if "interrupted" in low:
        return (f"Your query ran for more than {TIME_LIMIT_SECONDS:g} seconds and was stopped. "
                "Check for a missing JOIN condition or a recursive query that never ends.")
    if "too big" in low or "too long" in low or "too many" in low or "too deep" in low:
        return f"Your query exceeds a safety limit ({msg}). Please simplify it."
    if "no such table" in low or "no such column" in low:
        return f"SQL error: {msg}. Available tables: {', '.join(TABLES)}."
    if "one statement" in low or "multiple statements" in low or "more than one" in low:
        return "Only one SQL statement can be run at a time. Remove extra statements after the first semicolon."
    return f"SQL error: {msg}"


def _display(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<binary {len(value)} bytes>"
    return value


def run_query(db_path, sql, max_rows=MAX_DISPLAY_ROWS):
    """Run one read-only query and return a QueryResult, or raise SqlLabError."""
    sql = (sql or "").strip()
    if not sql:
        raise SqlLabError("Please type a query first.")
    if len(sql) > MAX_SQL_LENGTH:
        raise SqlLabError(f"Query is too long (maximum {MAX_SQL_LENGTH} characters).")
    if "\x00" in sql:
        raise SqlLabError("Query contains invalid characters.")

    conn = _connect_readonly(db_path)
    try:
        _apply_limits(conn)
        conn.set_authorizer(_authorizer)
        deadline = time.monotonic() + TIME_LIMIT_SECONDS
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, PROGRESS_STEP)

        cur = conn.execute(sql)
        if cur.description is None:
            raise SqlLabError("Only queries that return rows (SELECT) can be run here.")
        columns = [d[0] for d in cur.description]
        fetched = cur.fetchmany(max_rows + 1)
    except SqlLabError:
        raise
    except (sqlite3.Error, sqlite3.Warning, OverflowError, ValueError) as exc:
        raise SqlLabError(_friendly_error(exc, sql)) from None
    finally:
        conn.close()

    truncated = len(fetched) > max_rows
    rows = [tuple(_display(v) for v in row) for row in fetched[:max_rows]]
    return QueryResult(columns, rows, truncated)


# ---------------------------------------------------------------- helpers
def describe_tables(db_path, sample_rows=5):
    """Trusted helper (not student SQL): column info and a few sample rows per table."""
    conn = _connect_readonly(db_path)
    try:
        out = []
        for table in TABLES:  # fixed list of names, never user input
            cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
            rows = conn.execute(f"SELECT * FROM {table} LIMIT ?", (sample_rows,)).fetchall()
            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            out.append({"name": table, "total": total,
                        "columns": [{"name": c[1], "type": c[2], "pk": bool(c[5])} for c in cols],
                        "rows": rows})
        return out
    finally:
        conn.close()


def _norm_value(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(float(v), 2)
    return v


def _norm_rows(rows):
    return [tuple(_norm_value(v) for v in row) for row in rows]


def compare_results(expected, got, ordered):
    """Return (ok, message). Column names are ignored; values and row count must match."""
    if len(expected.columns) != len(got.columns):
        return False, (f"Your query returns {len(got.columns)} column(s) but the expected result "
                       f"has {len(expected.columns)}. Check which columns the question asks for.")
    exp, res = _norm_rows(expected.rows), _norm_rows(got.rows)
    if got.truncated or expected.truncated:
        return False, "Your query returns far more rows than expected."
    if len(exp) != len(res):
        return False, f"Your query returns {len(res)} row(s) but {len(exp)} were expected."

    def key(row):
        return [repr(v) for v in row]

    if sorted(exp, key=key) != sorted(res, key=key):
        return False, "The number of rows is right, but some values differ from the expected result."
    if ordered and exp != res:
        return False, "The right rows were returned, but not in the required order. Check your ORDER BY."
    return True, "Correct! Your result matches the expected output."
