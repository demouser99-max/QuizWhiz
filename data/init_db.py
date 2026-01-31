import sqlite3
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "quizwhiz.db")
CSV_FILE = os.path.join(BASE_DIR, "questions.csv")

os.makedirs(DATA_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Create table (NO topic column)
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id TEXT,
            username TEXT,
            score INTEGER
        )
    """)

    conn.commit()

    # Load CSV safely
    cur.execute("SELECT COUNT(*) FROM questions")
    if cur.fetchone()[0] == 0 and os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)

        # 🔥 DROP EXTRA COLUMNS (like topic)
        allowed_cols = [
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option"
        ]
        df = df[allowed_cols]

        df.to_sql("questions", conn, if_exists="append", index=False)

    conn.close()

init_db()
