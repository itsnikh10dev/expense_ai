import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "ocr_master.db"
TABLE_NAME = "ocr_line_items"


def _get_schema_description() -> str:
    """
    Reads the REAL table/column names straight from the database, so the
    prompt below can never drift out of sync with what actually exists.
    Falls back to a hard-coded description if the DB isn't there yet
    (e.g. before the first bill has ever been processed).
    """
    if DB_NAME.exists():
        try:
            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()
            cur.execute(f"PRAGMA table_info({TABLE_NAME})")
            cols = [row[1] for row in cur.fetchall()]
            con.close()
            if cols:
                return f"Table: {TABLE_NAME}\nColumns: {', '.join(cols)}"
        except sqlite3.Error:
            pass

    # Fallback — used only if the DB/table doesn't exist yet.
    return (
        f"Table: {TABLE_NAME}\n"
        "Columns: Invoice_No, Issue_Date, Category, Item, Amount"
    )


def user_query(user_input: str) -> str:
    schema = _get_schema_description()

    prompt = f"""You are a SQL generator for a SQLite database.

You may ONLY use the following table and columns. Do not invent, guess,
abbreviate, or rename any table or column. If a requested field does not
exist in this schema, use the closest existing column instead of inventing
a new one.

{schema}

Rules:
- Only output a single SQL query. No explanation, no markdown, no backticks.
- Only generate read-only queries: SELECT, WITH, or PRAGMA.
- Never use DELETE, UPDATE, DROP, ALTER, INSERT, TRUNCATE, ATTACH, DETACH,
  REPLACE, CREATE, or VACUUM.
- Always reference the table as "{TABLE_NAME}" exactly as written above.
- Use only the exact column names listed above, exactly as spelled and
  capitalized.

User question: {user_input}

SQL query:"""

    return prompt