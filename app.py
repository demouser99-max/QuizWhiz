import streamlit as st
import sqlite3
import random
import time
import uuid
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="QuizWhiz", layout="centered")

DB_PATH = "data/quizwhiz.db"
QUESTIONS_PER_QUIZ = 5
BASE_POINTS = 10

# ---------------- DB HELPERS ----------------
def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def fetch_random_questions(limit=5):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, question, option_a, option_b, option_c, option_d, correct_option FROM questions")
    rows = cur.fetchall()
    conn.close()
    return random.sample(rows, min(limit, len(rows)))

# ---------------- SESSION INIT ----------------
if "quizzes" not in st.session_state:
    st.session_state.quizzes = {}   # quiz_id -> questions

if "responses" not in st.session_state:
    st.session_state.responses = {} # quiz_id -> list of scores

# ---------------- UI ----------------
st.title("🎯 QuizWhiz")
st.caption("Real-time Online Quiz Platform")

params = st.query_params
quiz_id = params.get("quiz")

# ---------------- CREATE QUIZ ----------------
if not quiz_id:
    st.subheader("Create a New Quiz")

    if st.button("🚀 Create Quiz"):
        quiz_id = uuid.uuid4().hex[:6]
        questions = fetch_random_questions(QUESTIONS_PER_QUIZ)

        st.session_state.quizzes[quiz_id] = questions
        st.session_state.responses[quiz_id] = []

        st.query_params["quiz"] = quiz_id

        st.success("Quiz Created!")
        st.code(f"Quiz ID: {quiz_id}")
        st.stop()

# ---------------- JOIN QUIZ ----------------
st.subheader("📝 Join Quiz")

if quiz_id not in st.session_state.quizzes:
    st.error("Quiz not found or expired.")
    st.stop()

questions = st.session_state.quizzes[quiz_id]

username = st.text_input("Enter your name")

if not username:
    st.stop()

score = 0
start_time = time.time()

with st.form("quiz_form"):
    for i, q in enumerate(questions):
        qid, question, a, b, c, d, correct = q

        st.markdown(f"**Q{i+1}. {question}**")
        answer = st.radio(
            "",
            ["A", "B", "C", "D"],
            format_func=lambda x: {"A": a, "B": b, "C": c, "D": d}[x],
            key=f"{quiz_id}_{qid}"
        )

    submitted = st.form_submit_button("✅ Submit Quiz")

# ---------------- SUBMIT ----------------
if submitted:
    time_taken = max(1, int(time.time() - start_time))

    for i, q in enumerate(questions):
        correct_option = q[6]
        selected = st.session_state[f"{quiz_id}_{q[0]}"]

        if selected == correct_option:
            score += BASE_POINTS

    # Speed bonus
    if time_taken < 30:
        score += 2
    elif time_taken < 60:
        score += 1

    st.session_state.responses[quiz_id].append({
        "name": username,
        "score": score,
        "time": time_taken
    })

    st.success(f"🎉 Quiz Submitted! Your Score: {score}")

# ---------------- LEADERBOARD ----------------
if st.session_state.responses[quiz_id]:
    st.subheader("🏆 Leaderboard")

    leaderboard = sorted(
        st.session_state.responses[quiz_id],
        key=lambda x: (-x["score"], x["time"])
    )

    for i, entry in enumerate(leaderboard, start=1):
        st.write(f"{i}. **{entry['name']}** — {entry['score']} pts ⏱ {entry['time']}s")
