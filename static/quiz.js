const socket = io();
const { quizId, isHost } = window.QUIZ_CONTEXT;

const joinPanel = document.getElementById("join-panel");
const nameInput = document.getElementById("name-input");
const joinBtn = document.getElementById("join-btn");
const statusEl = document.getElementById("status");
const questionPanel = document.getElementById("question-panel");
const questionTitle = document.getElementById("question-title");
const optionsWrap = document.getElementById("options");
const leaderboardBody = document.getElementById("leaderboard-body");
const hostActions = document.getElementById("host-actions");
const startBtn = document.getElementById("start-btn");
const timerEl = document.getElementById("timer");

let joined = false;
let joinedName = "";
let selectedForCurrentQuestion = false;
let activeDeadline = null;
let timerHandle = null;

if (isHost) {
  hostActions.classList.remove("hidden");
}

joinBtn.addEventListener("click", () => {
  const name = nameInput.value.trim();
  socket.emit("join_quiz", { quiz_id: quizId, name });
});

if (startBtn) {
  startBtn.addEventListener("click", () => {
    socket.emit("start_quiz", { quiz_id: quizId });
  });
}

socket.on("join_error", (payload) => {
  statusEl.textContent = payload.message;
});

socket.on("join_success", () => {
  joined = true;
  joinedName = nameInput.value.trim();
  joinPanel.classList.add("hidden");
  statusEl.textContent = `Joined as ${joinedName}. Waiting for host...`;
});

socket.on("state_update", (state) => {
  updateLeaderboard(state.leaderboard || []);

  if (state.finished) {
    statusEl.textContent = "Quiz finished! Final leaderboard is shown.";
    questionPanel.classList.add("hidden");
    if (timerHandle) clearInterval(timerHandle);
    return;
  }

  if (!state.started) {
    statusEl.textContent = joined
      ? "Waiting for host to start the quiz."
      : "Join to enter the quiz.";
    questionPanel.classList.add("hidden");
    return;
  }

  if (!state.question) {
    questionPanel.classList.add("hidden");
    return;
  }

  renderQuestion(state.question);
  activeDeadline = state.deadline;
  startTimer();
});

function renderQuestion(question) {
  questionPanel.classList.remove("hidden");
  questionTitle.textContent = `Q${question.index + 1}/${question.total}: ${question.question}`;
  optionsWrap.innerHTML = "";
  selectedForCurrentQuestion = false;

  Object.entries(question.options).forEach(([key, value]) => {
    const button = document.createElement("button");
    button.className = "option-btn";
    button.textContent = `${key}. ${value}`;
    button.addEventListener("click", () => {
      if (!joined || selectedForCurrentQuestion) return;
      selectedForCurrentQuestion = true;
      button.classList.add("selected");
      socket.emit("submit_answer", { quiz_id: quizId, answer: key });
    });
    optionsWrap.appendChild(button);
  });
}

function updateLeaderboard(entries) {
  if (!entries.length) {
    leaderboardBody.innerHTML = `<tr><td colspan="5" class="muted">No players yet.</td></tr>`;
    return;
  }

  leaderboardBody.innerHTML = entries
    .map(
      (entry, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${entry.name}</td>
        <td>${entry.score}</td>
        <td>${entry.correct}</td>
        <td>${entry.answered}</td>
      </tr>`
    )
    .join("");
}

function startTimer() {
  if (timerHandle) clearInterval(timerHandle);
  if (!activeDeadline) {
    timerEl.textContent = "Time left: --";
    return;
  }

  const tick = () => {
    const secondsLeft = Math.max(0, Math.ceil(activeDeadline - Date.now() / 1000));
    timerEl.textContent = `Time left: ${secondsLeft}s`;
  };

  tick();
  timerHandle = setInterval(tick, 250);
}
