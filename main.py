from fastmcp import FastMCP
import os
import aiosqlite
import tempfile
import sqlite3
import json


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

CATEGORIES_PATH = os.path.join(
    os.path.dirname(__file__),
    "categories.json"
)

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as c:

            c.execute("PRAGMA journal_mode=WAL")

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

            # Test write access
            c.execute("""
                INSERT OR IGNORE INTO expenses
                (date, amount, category)
                VALUES ('2000-01-01', 0, 'test')
            """)

            c.execute("""
                DELETE FROM expenses
                WHERE category = 'test'
            """)

            c.commit()

            print("Database initialized successfully with write access")

    except Exception as e:
        print(f"Database initialization error: {e}")
        raise


init_db()


# ============================================================
# ADD EXPENSE
# ============================================================

@mcp.tool()
async def add_expense(
    date,
    amount,
    category,
    subcategory="",
    note=""
):
    """Add a new expense entry to the database."""

    try:

        async with aiosqlite.connect(DB_PATH) as c:

            cur = await c.execute(
                """
                INSERT INTO expenses
                (
                    date,
                    amount,
                    category,
                    subcategory,
                    note
                )
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

            expense_id = cur.lastrowid

            await c.commit()

            return {
                "status": "success",
                "id": expense_id,
                "message": "Expense added successfully"
            }

    except Exception as e:

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ============================================================
# LIST EXPENSES
# ============================================================

@mcp.tool()
async def list_expenses(
    start_date,
    end_date
):
    """List expense entries within an inclusive date range."""

    try:

        async with aiosqlite.connect(DB_PATH) as c:

            cur = await c.execute(
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
                ORDER BY date DESC, id DESC
                """,
                (
                    start_date,
                    end_date
                )
            )

            rows = await cur.fetchall()

            cols = [
                d[0]
                for d in cur.description
            ]

            return [
                dict(zip(cols, row))
                for row in rows
            ]

    except Exception as e:

        return {
            "status": "error",
            "message": f"Error listing expenses: {str(e)}"
        }


# ============================================================
# SUMMARIZE EXPENSES
# ============================================================

@mcp.tool()
async def summarize(
    start_date,
    end_date,
    category=None
):
    """Summarize expenses by category within a date range."""

    try:

        async with aiosqlite.connect(DB_PATH) as c:

            query = """
                SELECT
                    category,
                    SUM(amount) AS total_amount,
                    COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """

            params = [
                start_date,
                end_date
            ]

            if category:

                query += """
                    AND category = ?
                """

                params.append(category)

            query += """
                GROUP BY category
                ORDER BY total_amount DESC
            """

            cur = await c.execute(
                query,
                params
            )

            rows = await cur.fetchall()

            cols = [
                d[0]
                for d in cur.description
            ]

            return [
                dict(zip(cols, row))
                for row in rows
            ]

    except Exception as e:

        return {
            "status": "error",
            "message": f"Error summarizing expenses: {str(e)}"
        }


# ============================================================
# MODIFY EXPENSE
# ============================================================

@mcp.tool()
async def modify_expense(
    id: int,
    date=None,
    amount=None,
    category=None,
    subcategory=None,
    note=None
):
    """
    Modify an existing expense.

    Only the fields provided will be updated.
    """

    try:

        async with aiosqlite.connect(DB_PATH) as c:

            # --------------------------------------------
            # Check if expense exists
            # --------------------------------------------

            cur = await c.execute(
                """
                SELECT id
                FROM expenses
                WHERE id = ?
                """,
                (id,)
            )

            existing = await cur.fetchone()

            if existing is None:

                return {
                    "status": "error",
                    "message": f"No expense found with ID {id}"
                }


            # --------------------------------------------
            # Build UPDATE query
            # --------------------------------------------

            updates = []
            params = []

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


            # --------------------------------------------
            # Nothing to update
            # --------------------------------------------

            if not updates:

                return {
                    "status": "error",
                    "message": "No fields provided to update"
                }


            # ID for WHERE clause
            params.append(id)


            # --------------------------------------------
            # Execute UPDATE
            # --------------------------------------------

            query = f"""
                UPDATE expenses
                SET {", ".join(updates)}
                WHERE id = ?
            """

            await c.execute(
                query,
                params
            )

            await c.commit()


            return {
                "status": "success",
                "id": id,
                "message": f"Expense {id} updated successfully"
            }


    except Exception as e:

        return {
            "status": "error",
            "message": f"Error modifying expense: {str(e)}"
        }


# ============================================================
# DELETE EXPENSE
# ============================================================

@mcp.tool()
async def delete_expense(
    id: int
):
    """Delete an expense entry using its ID."""

    try:

        async with aiosqlite.connect(DB_PATH) as c:

            # --------------------------------------------
            # Check if expense exists
            # --------------------------------------------

            cur = await c.execute(
                """
                SELECT
                    id,
                    date,
                    amount,
                    category,
                    subcategory,
                    note
                FROM expenses
                WHERE id = ?
                """,
                (id,)
            )

            expense = await cur.fetchone()

            if expense is None:

                return {
                    "status": "error",
                    "message": f"No expense found with ID {id}"
                }


            # --------------------------------------------
            # Delete
            # --------------------------------------------

            await c.execute(
                """
                DELETE FROM expenses
                WHERE id = ?
                """,
                (id,)
            )

            await c.commit()


            return {
                "status": "success",
                "id": id,
                "deleted_expense": {
                    "date": expense[1],
                    "amount": expense[2],
                    "category": expense[3],
                    "subcategory": expense[4],
                    "note": expense[5]
                },
                "message": f"Expense {id} deleted successfully"
            }


    except Exception as e:

        return {
            "status": "error",
            "message": f"Error deleting expense: {str(e)}"
        }


# ============================================================
# CATEGORIES RESOURCE
# ============================================================

@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def categories():

    try:

        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }

        try:

            with open(
                CATEGORIES_PATH,
                "r",
                encoding="utf-8"
            ) as f:

                return f.read()

        except FileNotFoundError:

            return json.dumps(
                default_categories,
                indent=2
            )

    except Exception as e:

        return json.dumps({
            "error": f"Could not load categories: {str(e)}"
        })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )