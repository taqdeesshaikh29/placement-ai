from flask import Blueprint, render_template
from flask_login import current_user

from app.auth import student_required
from app.stats import get_dashboard_stats

main = Blueprint("main", __name__)

FEATURES = [
    {"icon": "bi-bar-chart-line", "title": "Aptitude Tests",
     "text": "Timed quantitative, logical and verbal quizzes with a full answer review."},
    {"icon": "bi-database", "title": "SQL Lab",
     "text": "Write real queries against a safe practice database and get them checked."},
    {"icon": "bi-code-slash", "title": "Python Practice",
     "text": "Output, fill-in-the-blank and multiple-choice questions on core Python."},
    {"icon": "bi-chat-dots", "title": "Interview Preparation",
     "text": "Technical and HR questions with key concepts, sample answers and your own saved answers."},
    {"icon": "bi-stars", "title": "AI Mock Interview",
     "text": "Answer one question at a time and get feedback. Without an AI key it runs in a clearly labelled fallback mode."},
    {"icon": "bi-graph-up-arrow", "title": "Progress Tracking",
     "text": "Charts of accuracy by subject and quiz scores over time, plus a review of your mistakes."},
]

STEPS = [
    ("Create your account", "Sign up with your email. It takes less than a minute."),
    ("Practise", "Take aptitude quizzes, solve SQL and Python questions and rehearse interviews."),
    ("Track and improve", "Review your mistakes and watch your accuracy improve."),
]


@main.route("/")
def index():
    return render_template("index.html", features=FEATURES, steps=STEPS)


@main.route("/dashboard")
@student_required
def dashboard():
    return render_template("dashboard.html", stats=get_dashboard_stats(current_user))
