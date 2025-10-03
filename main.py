import http
import os
import sqlite3
import aiosqlite
import tempfile
from fastmcp import FastMCP

TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__),"categories.json")

mcp = FastMCP("Expense Tracker")

def db_init():
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute(
                """
                    CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        amount REAL NOT NULL,
                        category TEXT NOT NULL,
                        subcategory TEXT DEFAULT '',
                        note TEXT DEFAULT ''
                    )
                """)
            # Test write access
            c.execute("INSERT OR IGNORE INTO expenses(date, amount, category)VALUES('2025-01-01',0,'test')")
            c.execute("DELETE FROM expenses WHERE category='test'")
            print("Database initialized successfully with write access")
    except Exception as e:
        print(f'Database initialization error: {e}')
        raise
    

        
db_init()

@mcp.tool
async def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry to expenses table"""
    try:
        with aiosqlite.connect(DB_PATH) as c:
            cur = c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note)VALUES(?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )
            return {"status": "Ok", "id": cur.lastrowid}
    except Exception as e:
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is in read-only mode. check file permission"}
        return {"status": "error", "message": f"Database error: {str(e)}"}    


@mcp.tool
async def list_expenses(startdate, enddate):
    """List the expenses for given date from the expense table"""
    try:
        with aiosqlite.connect(DB_PATH) as c:
            cur = c.execute(
                """
                SELECT id, date, amount, category, subcategory, note 
                FROM expenses
                WHERE date between ? AND ?
                ORDER BY id ASC
                """,
                (startdate, enddate)
            )

            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}
    
@mcp.tool
async def summarize(startdate, enddate, category=''):
    """Summarize the expenses between dates and category"""
    try:
        with aiosqlite.connect(DB_PATH) as c:
            query = (
                """
                SELECT category, SUM(amount) as Total_Amount
                FROM expenses
                WHERE date between ? AND ?
                """
            )
            params = [startdate, enddate]
            if category:
                query += " AND category = ?"
                params.append(category)
            query += " GROUP BY category ORDER BY category ASC"

            cur = c.execute(query, params)  

            cols = [d[0] for d in cur.description]
            return [dict(zip(cols,r)for r in cur.fetchall())]      
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}    
    
@mcp.resource(uri="expense://categories", mime_type ="application/json")    
def categories():
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
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        if "FileNotFoundError" in str(e):
            import json
            json.dumps(default_categories, indent=2)
        return f'{{"error": "could not load categories: {str(e)}}}'

@mcp.resource(uri="info://server")
def server_info()->str:
    """Get information about the server"""
    info ={
        "name": "Expense Tracker and Summarizer",
        "version": "1.0.0.",
        "description": "A simplistic expense tracker and summarizer",
        "tool": ["add_expense", "list_expenses", "summarize"],
        "author": "Samba"
    }

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
