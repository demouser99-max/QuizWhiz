import streamlit as st
import sqlite3
import time
from datetime import datetime
import random
import string
import ui
import os

# ------------------------
# Persistent DB path
# ------------------------
DB_FILE = "/data/quizwhiz.db"

# Create DB if missing
if not os.path.exists(DB_FILE):
    import init_db

# Connect with check_same_thread=False for multiple submissions
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# ------------------------
# Session state init
# ------------------------
if 'quiz_started' not in st.session_state:
    st.session_state['quiz_started'] = False
if 'question_index' not in st.session_state:
    st.session_state['question_index'] = 0
if 'score' not in st.session_state:
    st.session_state['score'] = 0
if 'questions' not in st.session_state:
    st.session_state['questions'] = []
if 'start_time' not in st.session_state:
    st.session_state['start_time'] = 0
if 'answer_times' not in st.session_state:
    st.session_state['answer_times'] = []

# ------------------------
# Helper: Generate Quiz ID
# ------------------------
def generate_quiz_id():
    return "QW" + ''.join(random.choices(string.digits, k=4))

# ------------------------
# Landing / Join
# ------------------------
st.title("🧠 QuizWhiz - Online Quiz Platform")

create_new = st.button("Create New Quiz")
quiz_id_input = st.text_input("Or Enter Quiz Link / ID to Join")
username = st.text_input("Enter Your Name")

if create_new:
    if username.strip() == "":
        st.warning("Enter name to create quiz!")
    else:
        quiz_id = generate_quiz_id()
        st.success(f"Quiz created! Quiz ID: {quiz_id}")
        st.session_state.update({
            'quiz_started': True,
            'username': username,
            'quiz_id': quiz_id,
            'question_index': 0,
            'score': 0,
            'answer_times': []
        })
        cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 10")
        st.session_state['questions'] = cursor.fetchall()
        st.session_state['start_time'] = time.time()
        st.experimental_rerun()

elif st.button("Join Quiz"):
    if username.strip() == "" or quiz_id_input.strip() == "":
        st.warning("Enter both name and quiz ID!")
    else:
        quiz_id = quiz_id_input.strip()
        st.session_state.update({
            'quiz_started': True,
            'username': username,
            'quiz_id': quiz_id,
            'question_index': 0,
            'score': 0,
            'answer_times': []
        })
        cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 10")
        st.session_state['questions'] = cursor.fetchall()
        st.session_state['start_time'] = time.time()
        st.success(f"Welcome {username}! Quiz {quiz_id} is starting...")
        st.experimental_rerun()

# ------------------------
# Quiz Logic
# ------------------------
if st.session_state['quiz_started']:
    questions = st.session_state['questions']
    idx = st.session_state['question_index']

    if idx < len(questions):
        q = questions[idx]
        answer, submit, shuffled_options, correct_option, question_id = ui.show_question(q, idx, st.session_state['start_time'])

        if submit:
            time_taken = time.time() - st.session_state['start_time']
            st.session_state['answer_times'].append(time_taken)

            points = 0
            if answer == correct_option:
                points = 2 if time_taken <= 10 else 1
            st.session_state['score'] += points

            # Safe submissions using immediate commit
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    quiz_id TEXT,
                    question_id INTEGER,
                    answer TEXT,
                    correct_option TEXT,
                    score INTEGER,
                    time_taken REAL,
                    timestamp TEXT
                )
            """)
            cursor.execute("""
                INSERT INTO responses (username, quiz_id, question_id, answer, correct_option, score, time_taken, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state['username'],
                st.session_state['quiz_id'],
                question_id,
                answer,
                correct_option,
                points,
                time_taken,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()

            # Next question
            st.session_state['start_time'] = time.time()
            st.session_state['question_index'] += 1
            st.experimental_rerun()

    else:
        ui.show_score(st.session_state['score'], len(questions)*2)

        cursor.execute("""
            SELECT username, SUM(score) as total_score
            FROM responses
            WHERE quiz_id = ?
            GROUP BY username
            ORDER BY total_score DESC
        """, (st.session_state['quiz_id'],))
        leaderboard = cursor.fetchall()
        ui.show_leaderboard(leaderboard)
