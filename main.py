from pathlib import Path
import sqlite3
from fastmcp import FastMCP

mcp = FastMCP("ExpenseTracker")

# --------------------------------------------------
# Database configuration
# --------------------------------------------------

DATA_DIR = Path.home() / "ExpenseTrackerData"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "expenses.db"

CATEGORIES_PATH = Path(__file__).parent / "categories.json"

print(f"Database path: {DB_PATH}")


# --------------------------------------------------
# Initialize database
# --------------------------------------------------

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


# --------------------------------------------------
# ADD EXPENSE
# --------------------------------------------------

@mcp.tool()
def add_expense(
    date,
    amount,
    category,
    subcategory="",
    note=""
):
    """Add a new expense entry to the database."""

    with sqlite3.connect(str(DB_PATH)) as c:

        cur = c.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                date,
                amount,
                category,
                subcategory,
                note
            )
        )

        c.commit()

        return {
            "status": "ok",
            "id": cur.lastrowid,
            "message": "Expense added successfully"
        }


# --------------------------------------------------
# LIST EXPENSES
# --------------------------------------------------

@mcp.tool()
def list_expenses(start_date, end_date):
    """List expense entries within an inclusive date range."""

    with sqlite3.connect(str(DB_PATH)) as c:

        cur = c.execute(
            """
            SELECT
                id,
                date,
                amount,
                category,
                subcategory,
                note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (
                start_date,
                end_date
            )
        )

        cols = [d[0] for d in cur.description]

        return [
            dict(zip(cols, row))
            for row in cur.fetchall()
        ]


# --------------------------------------------------
# SUMMARIZE
# --------------------------------------------------

@mcp.tool()
def summarize(
    start_date,
    end_date,
    category=None
):
    """Summarize expenses by category."""

    with sqlite3.connect(str(DB_PATH)) as c:

        query = """
            SELECT
                category,
                SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [
            start_date,
            end_date
        ]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += """
            GROUP BY category
            ORDER BY category ASC
        """

        cur = c.execute(
            query,
            params
        )

        cols = [d[0] for d in cur.description]

        return [
            dict(zip(cols, row))
            for row in cur.fetchall()
        ]


# --------------------------------------------------
# DELETE EXPENSE
# --------------------------------------------------

@mcp.tool()
def delete_expense(id: int):
    """Delete an expense entry using its ID."""

    with sqlite3.connect(str(DB_PATH)) as c:

        cur = c.execute(
            """
            DELETE FROM expenses
            WHERE id = ?
            """,
            (id,)
        )

        c.commit()

        if cur.rowcount == 0:
            return {
                "status": "error",
                "message": f"No expense found with ID {id}"
            }

        return {
            "status": "ok",
            "id": id,
            "message": f"Expense {id} deleted successfully"
        }


# --------------------------------------------------
# MODIFY EXPENSE
# --------------------------------------------------

@mcp.tool()
def modify_expense(
    id: int,
    date=None,
    amount=None,
    category=None,
    subcategory=None,
    note=None
):
    """
    Modify an existing expense.

    Only the fields provided by the user will be updated.
    """

    with sqlite3.connect(str(DB_PATH)) as c:

        # Check whether expense exists
        cur = c.execute(
            """
            SELECT id
            FROM expenses
            WHERE id = ?
            """,
            (id,)
        )

        if cur.fetchone() is None:
            return {
                "status": "error",
                "message": f"No expense found with ID {id}"
            }

        updates = []
        params = []

        # Build UPDATE dynamically
        if date is not None:
            updates.append("date = ?")
            params.append(date)

        if amount is not None:
            updates.append("amount = ?")
            params.append(amount)

        if category is not None:
            updates.append("category = ?")
            params.append(category)

        if subcategory is not None:
            updates.append("subcategory = ?")
            params.append(subcategory)

        if note is not None:
            updates.append("note = ?")
            params.append(note)

        # Nothing to update
        if not updates:
            return {
                "status": "error",
                "message": "No fields provided to update"
            }

        # Add ID for WHERE clause
        params.append(id)

        query = f"""
            UPDATE expenses
            SET {", ".join(updates)}
            WHERE id = ?
        """

        c.execute(
            query,
            params
        )

        c.commit()

        return {
            "status": "ok",
            "id": id,
            "message": f"Expense {id} updated successfully"
        }


# --------------------------------------------------
# CATEGORIES RESOURCE
# --------------------------------------------------

@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def categories():

    with open(
        CATEGORIES_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return f.read()


# --------------------------------------------------
# START MCP SERVER
# --------------------------------------------------

if __name__ == "__main__":

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8001
    )