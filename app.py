import streamlit as st
import sqlite3
import uuid
import random
import csv
import os
import time

st.set_page_config("QuizWhiz", layout="centered")

DB = "quizwhiz.db"
CSV_FILE = "questions.csv"
QUESTIONS_PER_QUIZ = 5

# ---------------- DB ----------------
def db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        a TEXT, b TEXT, c TEXT, d TEXT,
        correct TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        quiz_id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS quiz_questions (
        quiz_id TEXT,
        question_id INTEGER
    )
    """)

    # Load CSV only once
    c.execute("SELECT COUNT(*) FROM questions")
    if c.fetchone()[0] == 0:
        if not os.path.exists(CSV_FILE):
            st.error("questions.csv missing")
            st.stop()

        with open(CSV_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                c.execute("""
                INSERT INTO questions
                (question, a, b, c, d, correct)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    r["question"],
                    r["option_a"],
                    r["option_b"],
                    r["option_c"],
                    r["option_d"],
                    r["correct_option"]
                ))
    conn.commit()
    conn.close()

init_db()

# ---------------- HELPERS ----------------
def create_quiz():
    conn = db()
    c = conn.cursor()

    quiz_id = uuid.uuid4().hex[:6]
    c.execute("INSERT INTO quizzes (quiz_id) VALUES (?)", (quiz_id,))

    c.execute("SELECT id FROM questions ORDER BY RANDOM() LIMIT ?", (QUESTIONS_PER_QUIZ,))
    qs = c.fetchall()

    for q in qs:
        c.execute("INSERT INTO quiz_questions VALUES (?, ?)", (quiz_id, q[0]))

    conn.commit()
    conn.close()
    return quiz_id

def load_quiz(quiz_id):
    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT q.id, q.question, q.a, q.b, q.c, q.d, q.correct
    FROM questions q
    JOIN quiz_questions qq ON q.id = qq.question_id
    WHERE qq.quiz_id = ?
    """, (quiz_id,))

    data = c.fetchall()
    conn.close()
    return data

# ---------------- UI ----------------
st.title("🎯 QuizWhiz")
st.caption("Real-time Online Quiz Platform")

quiz_id = st.query_params.get("quiz")

if not quiz_id:
    st.subheader("Create a New Quiz")
    if st.button("🚀 Create Quiz"):
        quiz_id = create_quiz()
        st.query_params["quiz"] = quiz_id
        st.success("Quiz Created!")
        st.code(f"Share this Quiz ID: {quiz_id}")
        st.stop()

questions = load_quiz(quiz_id)

if not questions:
    st.error("Quiz expired or invalid link.")
    st.stop()

name = st.text_input("Enter your name")
if not name:
    st.stop()

start = time.time()
answers = {}

with st.form("quiz"):
    for i, q in enumerate(questions):
        answers[q[0]] = st.radio(
            f"Q{i+1}. {q[1]}",
            ["A", "B", "C", "D"],
            format_func=lambda x: {"A": q[2], "B": q[3], "C": q[4], "D": q[5]}[x]
        )
    submit = st.form_submit_button("Submit")

if submit:
    score = sum(1 for q in questions if answers[q[0]] == q[6]) * 10
    st.success(f"🎉 Score: {score}")
