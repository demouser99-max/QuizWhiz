import streamlit as st
import random
import time

# ------------------------
# Add custom CSS for colors and animations
# ------------------------
def set_styles():
    st.markdown("""
        <style>
        /* Background gradient */
        body {
            background: linear-gradient(to right, #6a11cb, #2575fc);
            color: #ffffff;
        }
        /* Card style for questions */
        .question-card {
            background-color: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            animation: fadeIn 1s;
        }
        /* Fade-in animation */
        @keyframes fadeIn {
            from {opacity: 0;}
            to {opacity: 1;}
        }
        /* Buttons */
        .stButton>button {
            background: linear-gradient(to right, #ff416c, #ff4b2b);
            color: white;
            font-weight: bold;
            border-radius: 10px;
            padding: 10px 20px;
            margin-top: 10px;
            transition: transform 0.2s;
        }
        .stButton>button:hover {
            transform: scale(1.05);
            cursor: pointer;
        }
        </style>
    """, unsafe_allow_html=True)

# ------------------------
# Landing / Join Quiz
# ------------------------
def show_join_screen():
    set_styles()
    st.markdown("<h1 style='text-align:center;'>🧠 QuizWhiz - Online Quiz Platform</h1>", unsafe_allow_html=True)
    quiz_id = st.text_input("Enter Quiz Link / ID", value="QW1001")
    username = st.text_input("Enter Your Name")
    join = st.button("Join Quiz")
    return quiz_id, username, join

# ------------------------
# Show a single question with card style
# ------------------------
def show_question(q, idx, start_time):
    question_id = q[0]
    question_text = q[1]
    options = [q[2], q[3], q[4], q[5]]
    correct_option = q[6]

    shuffled_options = options.copy()
    random.shuffle(shuffled_options)

    st.markdown(f"<div class='question-card'><h3>Q{idx+1}: {question_text}</h3></div>", unsafe_allow_html=True)
    answer = st.radio("Select your answer:", shuffled_options, key=idx)

    submit = st.button("Submit Answer")
    return answer, submit, shuffled_options, correct_option, question_id

# ------------------------
# Show final score with confetti animation
# ------------------------
def show_score(score, total):
    st.balloons()
    st.markdown(f"<h2 style='color:#ffdf00;'>🎉 Quiz Completed! Your Score: {score} / {total}</h2>", unsafe_allow_html=True)

# ------------------------
# Show colorful leaderboard
# ------------------------
def show_leaderboard(leaderboard):
    st.subheader("🏆 Leaderboard")
    colors = ["#FF5733", "#FFC300", "#DAF7A6", "#FF33FF", "#33FFF6"]
    for i, row in enumerate(leaderboard, start=1):
        color = colors[i % len(colors)]
        st.markdown(f"<p style='color:{color}; font-weight:bold;'>{i}. {row[0]} - {row[1]} points</p>", unsafe_allow_html=True)
