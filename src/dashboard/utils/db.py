import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")

def get_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    # Return rows as dictionary-like objects for easier JSON/DataFrame mapping
    conn.row_factory = sqlite3.Row
    return conn
