import sqlite3
import os
import pandas as pd

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "quizwhiz.db")
CSV_FILE = os.path.join(BASE_DIR, "questions.csv")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Questions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_option TEXT
        )
    """)

    # Scores table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id TEXT,
            username TEXT,
            score INTEGER
        )
    """)

    conn.commit()

    # Load CSV questions only once
    cur.execute("SELECT COUNT(*) FROM questions")
    count = cur.fetchone()[0]

    if count == 0 and os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df.to_sql("questions", conn, if_exists="append", index=False)

    conn.close()

# Run on import
init_db()
