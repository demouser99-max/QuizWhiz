import csv
import os
import random
import sqlite3
import threading
import time
import uuid

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_socketio import SocketIO, emit, join_room

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "quizwhiz.db")
CSV_PATH = os.path.join(BASE_DIR, "questions.csv")
QUESTIONS_PER_QUIZ = 8
QUESTION_TIME_LIMIT_SECONDS = 15

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "quizwhiz-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

quiz_state_lock = threading.Lock()
quiz_states = {}


def db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_questions (
            quiz_id TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            PRIMARY KEY (quiz_id, question_id),
            FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
        """
    )

    cur.execute("SELECT COUNT(*) FROM questions")
    has_questions = cur.fetchone()[0] > 0

    if not has_questions:
        if not os.path.exists(CSV_PATH):
            raise FileNotFoundError("questions.csv is missing")

        with open(CSV_PATH, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            records = [
                (
                    row["question"],
                    row["option_a"],
                    row["option_b"],
                    row["option_c"],
                    row["option_d"],
                    row["correct_option"],
                )
                for row in reader
            ]

        cur.executemany(
            """
            INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_option)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    conn.commit()
    conn.close()


def create_quiz():
    conn = db_connection()
    cur = conn.cursor()

    quiz_id = uuid.uuid4().hex[:7]
    cur.execute("INSERT INTO quizzes (quiz_id) VALUES (?)", (quiz_id,))

    cur.execute(
        "SELECT id FROM questions ORDER BY RANDOM() LIMIT ?", (QUESTIONS_PER_QUIZ,)
    )
    question_rows = cur.fetchall()

    for idx, row in enumerate(question_rows):
        cur.execute(
            "INSERT INTO quiz_questions (quiz_id, question_id, position) VALUES (?, ?, ?)",
            (quiz_id, row[0], idx),
        )

    conn.commit()
    conn.close()

    with quiz_state_lock:
        quiz_states[quiz_id] = {
            "started": False,
            "finished": False,
            "current_question": -1,
            "question_started_at": None,
            "question_deadline": None,
            "participants": {},
            "answers_for_question": {},
        }

    return quiz_id


def load_quiz_questions(quiz_id):
    conn = db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.id, q.question, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_option
        FROM quiz_questions qq
        JOIN questions q ON q.id = qq.question_id
        WHERE qq.quiz_id = ?
        ORDER BY qq.position ASC
        """,
        (quiz_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def ensure_quiz_exists(quiz_id):
    conn = db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM quizzes WHERE quiz_id = ?", (quiz_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def leaderboard_payload(state):
    participants = sorted(
        state["participants"].values(),
        key=lambda p: (-p["score"], p["total_answer_time"], p["name"].lower()),
    )
    return [
        {
            "name": p["name"],
            "score": p["score"],
            "correct": p["correct"],
            "answered": p["answered"],
        }
        for p in participants
    ]


def emit_quiz_state(quiz_id):
    with quiz_state_lock:
        if quiz_id not in quiz_states:
            return

        state = quiz_states[quiz_id]
        questions = load_quiz_questions(quiz_id)
        total_questions = len(questions)

        if state["current_question"] >= 0 and state["current_question"] < total_questions:
            q = questions[state["current_question"]]
            question_payload = {
                "index": state["current_question"],
                "total": total_questions,
                "id": q[0],
                "question": q[1],
                "options": {"A": q[2], "B": q[3], "C": q[4], "D": q[5]},
            }
        else:
            question_payload = None

        payload = {
            "started": state["started"],
            "finished": state["finished"],
            "leaderboard": leaderboard_payload(state),
            "question": question_payload,
            "deadline": state["question_deadline"],
            "time_limit": QUESTION_TIME_LIMIT_SECONDS,
        }

    socketio.emit("state_update", payload, room=quiz_id)


def advance_question(quiz_id):
    with quiz_state_lock:
        state = quiz_states.get(quiz_id)
        if not state or state["finished"]:
            return

        questions = load_quiz_questions(quiz_id)
        next_index = state["current_question"] + 1

        if next_index >= len(questions):
            state["finished"] = True
            state["question_deadline"] = None
            state["question_started_at"] = None
        else:
            state["current_question"] = next_index
            state["answers_for_question"] = {}
            now = time.time()
            state["question_started_at"] = now
            state["question_deadline"] = now + QUESTION_TIME_LIMIT_SECONDS

    emit_quiz_state(quiz_id)


def timer_worker():
    while True:
        now = time.time()
        to_advance = []
        with quiz_state_lock:
            for quiz_id, state in quiz_states.items():
                if (
                    state["started"]
                    and not state["finished"]
                    and state["question_deadline"]
                    and now >= state["question_deadline"]
                ):
                    to_advance.append(quiz_id)

        for quiz_id in to_advance:
            advance_question(quiz_id)

        socketio.sleep(0.5)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create", methods=["POST"])
def create():
    quiz_id = create_quiz()
    join_link = request.url_root.rstrip("/") + url_for("quiz_room", quiz_id=quiz_id)
    host_link = f"{join_link}?host=1"
    return jsonify({"quiz_id": quiz_id, "join_link": join_link, "host_link": host_link})


@app.route("/quiz/<quiz_id>")
def quiz_room(quiz_id):
    if not ensure_quiz_exists(quiz_id):
        return redirect(url_for("index"))

    is_host = request.args.get("host") == "1"
    return render_template("quiz.html", quiz_id=quiz_id, is_host=is_host)


@socketio.on("join_quiz")
def on_join_quiz(data):
    quiz_id = data.get("quiz_id", "").strip()
    name = data.get("name", "").strip()

    if not quiz_id or not ensure_quiz_exists(quiz_id):
        emit("join_error", {"message": "Invalid quiz link."})
        return

    if not name:
        emit("join_error", {"message": "Please enter your name."})
        return

    join_room(quiz_id)

    with quiz_state_lock:
        state = quiz_states.setdefault(
            quiz_id,
            {
                "started": False,
                "finished": False,
                "current_question": -1,
                "question_started_at": None,
                "question_deadline": None,
                "participants": {},
                "answers_for_question": {},
            },
        )

        existing_names = {p["name"].lower() for p in state["participants"].values()}
        if request.sid not in state["participants"] and name.lower() in existing_names:
            emit("join_error", {"message": "Name already taken in this quiz."})
            return

        participant = state["participants"].get(request.sid, None)
        if participant is None:
            state["participants"][request.sid] = {
                "name": name,
                "score": 0,
                "correct": 0,
                "answered": 0,
                "total_answer_time": 0.0,
            }

    emit("join_success", {"quiz_id": quiz_id})
    emit_quiz_state(quiz_id)


@socketio.on("start_quiz")
def on_start_quiz(data):
    quiz_id = data.get("quiz_id", "").strip()
    with quiz_state_lock:
        state = quiz_states.get(quiz_id)
        if not state or state["started"]:
            return
        state["started"] = True

    advance_question(quiz_id)


@socketio.on("submit_answer")
def on_submit_answer(data):
    quiz_id = data.get("quiz_id", "").strip()
    selected = data.get("answer", "").strip().upper()

    if selected not in {"A", "B", "C", "D"}:
        return

    with quiz_state_lock:
        state = quiz_states.get(quiz_id)
        if not state or state["finished"] or not state["started"]:
            return

        participant = state["participants"].get(request.sid)
        if not participant:
            return

        q_index = state["current_question"]
        if q_index < 0:
            return

        answer_key = (request.sid, q_index)
        if answer_key in state["answers_for_question"]:
            return

        questions = load_quiz_questions(quiz_id)
        if q_index >= len(questions):
            return

        current_question = questions[q_index]
        correct_answer = current_question[6].upper()
        elapsed = max(0.0, time.time() - (state["question_started_at"] or time.time()))

        participant["answered"] += 1
        participant["total_answer_time"] += elapsed

        if selected == correct_answer:
            points = max(20, int(100 - elapsed * 6))
            participant["score"] += points
            participant["correct"] += 1

        state["answers_for_question"][answer_key] = selected

    emit_quiz_state(quiz_id)


@socketio.on("disconnect")
def on_disconnect():
    with quiz_state_lock:
        for quiz_id, state in quiz_states.items():
            if request.sid in state["participants"]:
                del state["participants"][request.sid]
                socketio.emit(
                    "state_update",
                    {
                        "started": state["started"],
                        "finished": state["finished"],
                        "leaderboard": leaderboard_payload(state),
                        "question": None,
                        "deadline": state["question_deadline"],
                        "time_limit": QUESTION_TIME_LIMIT_SECONDS,
                    },
                    room=quiz_id,
                )
                break


if __name__ == "__main__":
    init_db()
    socketio.start_background_task(timer_worker)
    port = int(os.environ.get("PORT", "5000"))
    socketio.run(app, host="0.0.0.0", port=port)
else:
    init_db()
    socketio.start_background_task(timer_worker)
