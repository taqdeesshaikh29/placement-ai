const form = document.getElementById("quizForm");
const submitBtn = document.getElementById("submitBtn");
const timerEl = document.getElementById("timer");

const deadline = Date.now() + parseInt(timerEl.dataset.remaining, 10) * 1000;
let remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
let submitted = false;

function submitOnce() {
  if (submitted) return;
  submitted = true;
  submitBtn.disabled = true;
  submitBtn.textContent = "Submitting...";
  form.submit();
}

function render() {
  const m = String(Math.floor(remaining / 60)).padStart(2, "0");
  const s = String(remaining % 60).padStart(2, "0");
  timerEl.textContent = `${m}:${s}`;
  timerEl.parentElement.classList.toggle("timer-low", remaining <= 30);
}

form.addEventListener("submit", (e) => {
  if (submitted) { e.preventDefault(); return; }
  submitted = true;
  submitBtn.disabled = true;
  submitBtn.textContent = "Submitting...";
});

render();
const tick = setInterval(() => {
  remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
  if (remaining <= 0) {
    remaining = 0;
    render();
    clearInterval(tick);
    submitOnce();
    return;
  }
  render();
}, 1000);
