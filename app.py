import streamlit as st
import sqlite3
import random
import uuid
import time
import csv
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="QuizWhiz", layout="centered")

DB_PATH = "quizwhiz.db"
CSV_PATH = "questions.csv"
QUESTIONS_PER_QUIZ = 5
BASE_POINTS = 10

# ---------------- DATABASE SETUP ----------------
def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Create table if not exists
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

    # Check if table is empty
    cur.execute("SELECT COUNT(*) FROM questions")
    count = cur.fetchone()[0]

    # Load CSV only once
    if count == 0 and os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cur.execute("""
                    INSERT INTO questions 
                    (question, option_a, option_b, option_c, option_d, correct_option)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row["question"],
                    row["option_a"],
                    row["option_b"],
                    row["option_c"],
                    row["option_d"],
                    row["correct_option"]
                ))
        conn.commit()

    conn.close()

# Initialize DB safely
init_db()

# ---------------- HELPERS ----------------
def fetch_random_questions(limit):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, question, option_a, option_b, option_c, option_d, correct_option 
        FROM questions
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    return random.sample(rows, min(limit, len(rows)))

# ---------------- SESSION STATE ----------------
if "quizzes" not in st.session_state:
    st.session_state.quizzes = {}

if "responses" not in st.session_state:
    st.session_state.responses = {}

# ---------------- UI ----------------
st.title("🎯 QuizWhiz")
st.caption("Real-time Online Quiz Platform")

quiz_id = st.query_params.get("quiz")

# ---------------- CREATE QUIZ ----------------
if not quiz_id:
    st.subheader("Create a New Quiz")

    if st.button("🚀 Create Quiz"):
        questions = fetch_random_questions(QUESTIONS_PER_QUIZ)

        if not questions:
            st.error("No questions found. Check questions.csv")
            st.stop()

        quiz_id = uuid.uuid4().hex[:6]
        st.session_state.quizzes[quiz_id] = questions
        st.session_state.responses[quiz_id] = []

        st.query_params["quiz"] = quiz_id
        st.success("Quiz Created!")
        st.code(f"Share this Quiz ID: {quiz_id}")
        st.stop()

# ---------------- JOIN QUIZ ----------------
if quiz_id not in st.session_state.quizzes:
    st.error("Quiz expired or invalid link.")
    st.stop()

questions = st.session_state.quizzes[quiz_id]

name = st.text_input("Enter your name")
if not name:
    st.stop()

score = 0
start_time = time.time()

with st.form("quiz_form"):
    answers = {}
    for i, q in enumerate(questions):
        qid, question, a, b, c, d, correct = q
        st.markdown(f"**Q{i+1}. {question}**")
        answers[qid] = st.radio(
            "",
            ["A", "B", "C", "D"],
            format_func=lambda x: {"A": a, "B": b, "C": c, "D": d}[x],
            key=f"{quiz_id}_{qid}"
        )

    submitted = st.form_submit_button("✅ Submit Quiz")

# ---------------- SUBMIT ----------------
if submitted:
    time_taken = max(1, int(time.time() - start_time))

    for q in questions:
        if answers[q[0]] == q[6]:
            score += BASE_POINTS

    if time_taken < 30:
        score += 2
    elif time_taken < 60:
        score += 1

    st.session_state.responses[quiz_id].append({
        "name": name,
        "score": score,
        "time": time_taken
    })

    st.success(f"🎉 Your Score: {score}")

# ---------------- LEADERBOARD ----------------
if st.session_state.responses[quiz_id]:
    st.subheader("🏆 Leaderboard")

    leaderboard = sorted(
        st.session_state.responses[quiz_id],
        key=lambda x: (-x["score"], x["time"])
    )

    for i, r in enumerate(leaderboard, 1):
        st.write(f"{i}. **{r['name']}** — {r['score']} pts ⏱ {r['time']}s")
