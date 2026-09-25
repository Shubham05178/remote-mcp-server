from pathlib import Path
import sqlite3
import json
from fastmcp import FastMCP

mcp = FastMCP("ExpenseTracker")

# Writable location in user's home directory
DATA_DIR = Path.home() / "ExpenseTrackerData"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "expenses.db"

CATEGORIES_PATH = Path(__file__).parent / "categories.json"

print(f"Database path: {DB_PATH}")


def init_db():
    with sqlite3.connect(str(DB_PATH)) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        c.commit()


init_db()


@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry to the database."""

    with sqlite3.connect(str(DB_PATH)) as c:
        cur = c.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note)
        )

        c.commit()

        return {
            "status": "ok",
            "id": cur.lastrowid
        }


@mcp.tool()
def list_expenses(start_date, end_date):
    """List expense entries within an inclusive date range."""

    with sqlite3.connect(str(DB_PATH)) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )

        cols = [d[0] for d in cur.description]

        return [
            dict(zip(cols, row))
            for row in cur.fetchall()
        ]


@mcp.tool()
def summarize(start_date, end_date, category=None):
    """Summarize expenses by category."""

    with sqlite3.connect(str(DB_PATH)) as c:

        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += """
            GROUP BY category
            ORDER BY category ASC
        """

        cur = c.execute(query, params)

        cols = [d[0] for d in cur.description]

        return [
            dict(zip(cols, row))
            for row in cur.fetchall()
        ]


@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def categories():

    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )