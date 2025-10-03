import http
import os
import sqlite3
from fastmcp import FastMCP

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__),"categories.json")

mcp = FastMCP("Expense Tracker")

def db_init():
    with sqlite3.connect(DB_PATH) as c:
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
        
db_init()

@mcp.tool
def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry to expenses table"""

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note)VALUES(?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "Ok", "id": cur.lastrowid}


@mcp.tool
def list_expenses(startdate, enddate):
    """List the expenses for given date from the expense table"""

    with sqlite3.connect(DB_PATH) as c:
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

@mcp.tool
def summarize(startdate, enddate, category=''):
    """Summarize the expenses between dates and category"""
    with sqlite3.connect(DB_PATH) as c:
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
@mcp.resource(uri="expense://categories", mime_type ="application/json")    
def categories():
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

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
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
