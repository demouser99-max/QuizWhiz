import streamlit as st
import sqlite3
import os
import uuid
import random
import time

# Initialize DB
import data.init_db as init_db

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data", "quizwhiz.db")

# DB connection
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

st.set_page_config(page_title="QuizWhiz", layout="centered")

# Session state
if "quiz_id" not in st.session_state:
    st.session_state.quiz_id = None
if "score" not in st.session_state:
    st.session_state.score = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = None

st.title("🎯 QuizWhiz")
st.subheader("Real-time Online Quiz Platform")

menu = st.sidebar.radio("Menu", ["Create Quiz", "Join Quiz", "Leaderboard"])

# ---------------- CREATE QUIZ ----------------
if menu == "Create Quiz":
    st.header("🛠 Create a Quiz")

    if st.button("Generate Quiz"):
        quiz_id = str(uuid.uuid4())[:6]
        st.session_state.quiz_id = quiz_id
        st.success(f"Quiz Created!")
        st.code(f"{st.experimental_get_query_params()}?quiz={quiz_id}")

        st.write("📌 Share this Quiz ID:", quiz_id)

# ---------------- JOIN QUIZ ----------------
elif menu == "Join Quiz":
    st.header("🚀 Join Quiz")

    quiz_id = st.text_input("Enter Quiz ID")
    username = st.text_input("Your Name")

    if st.button("Start Quiz") and quiz_id and username:
        st.session_state.quiz_id = quiz_id
        st.session_state.score = 0
        st.session_state.start_time = time.time()

        cur.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 5")
        questions = cur.fetchall()

        for q in questions:
            st.subheader(q[1])
            options = {
                "A": q[2],
                "B": q[3],
                "C": q[4],
                "D": q[5]
            }

            user_ans = st.radio(
                "Choose an option:",
                options.keys(),
                format_func=lambda x: options[x],
                key=str(q[0])
            )

            if st.button(f"Submit Q{q[0]}"):
                time_taken = time.time() - st.session_state.start_time
                if user_ans == q[6]:
                    st.session_state.score += 5 if time_taken < 10 else 3
                    st.success("Correct!")
                else:
                    st.error("Wrong!")

        # Save score
        cur.execute(
            "INSERT INTO scores (quiz_id, username, score) VALUES (?, ?, ?)",
            (quiz_id, username, st.session_state.score)
        )
        conn.commit()

        st.success(f"Quiz Completed! Score: {st.session_state.score}")

# ---------------- LEADERBOARD ----------------
elif menu == "Leaderboard":
    st.header("🏆 Leaderboard")

    quiz_id = st.text_input("Enter Quiz ID to view leaderboard")

    if quiz_id:
        cur.execute(
            "SELECT username, score FROM scores WHERE quiz_id=? ORDER BY score DESC",
            (quiz_id,)
        )
        results = cur.fetchall()

        if results:
            for i, r in enumerate(results, 1):
                st.write(f"#{i} {r[0]} — {r[1]} points")
        else:
            st.info("No results yet.")

