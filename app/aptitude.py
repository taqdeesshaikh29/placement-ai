import random
import secrets
import time

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app.auth import student_required
from app.extensions import db
from app.models import AptitudeAttempt, AttemptAnswer, Question, QuizResult
from app.seed_data import LOGIC, QUANT, VERBAL

aptitude = Blueprint("aptitude", __name__, url_prefix="/aptitude")

CATEGORIES = [
    {"name": QUANT, "icon": "bi-calculator", "text": "Percentages, ratios, time & work, interest and more."},
    {"name": LOGIC, "icon": "bi-puzzle", "text": "Series, coding-decoding, relations and deductions."},
    {"name": VERBAL, "icon": "bi-book", "text": "Vocabulary, grammar, idioms and sentence skills."},
]
DIFFICULTIES = ["Easy", "Medium", "Hard", "Mixed"]
QUESTIONS_PER_QUIZ = 5
SECONDS_PER_QUESTION = 90
GRACE_SECONDS = 30  # allowance for network delay when the timer auto-submits


@aptitude.route("/")
@student_required
def index():
    return render_template("aptitude/index.html", categories=CATEGORIES, difficulties=DIFFICULTIES)


@aptitude.route("/start", methods=["POST"])
@student_required
def start():
    category = request.form.get("category", "")
    difficulty = request.form.get("difficulty", "")
    if category not in {c["name"] for c in CATEGORIES} or difficulty not in DIFFICULTIES:
        flash("Please choose a valid category and difficulty.", "danger")
        return redirect(url_for("aptitude.index"))

    query = Question.query.filter_by(category=category)
    if difficulty != "Mixed":
        query = query.filter_by(difficulty=difficulty)
    ids = [q.id for q in query.with_entities(Question.id).all()]
    if not ids:
        flash("No questions are available for that selection yet.", "warning")
        return redirect(url_for("aptitude.index"))

    chosen = random.sample(ids, min(QUESTIONS_PER_QUIZ, len(ids)))
    session["quiz"] = {
        "token": secrets.token_urlsafe(16),
        "category": category,
        "difficulty": difficulty,
        "ids": chosen,
        "started": int(time.time()),
        "limit": SECONDS_PER_QUESTION * len(chosen),
    }
    return redirect(url_for("aptitude.quiz"))


@aptitude.route("/quiz")
@student_required
def quiz():
    state = session.get("quiz")
    if not state:
        flash("Start a quiz to begin.", "info")
        return redirect(url_for("aptitude.index"))

    by_id = {q.id: q for q in Question.query.filter(Question.id.in_(state["ids"])).all()}
    questions = [by_id[i] for i in state["ids"] if i in by_id]
    remaining = max(0, state["limit"] - (int(time.time()) - state["started"]))
    return render_template("aptitude/quiz.html", state=state, questions=questions, remaining=remaining)


@aptitude.route("/submit", methods=["POST"])
@student_required
def submit():
    token = request.form.get("token", "")
    state = session.get("quiz")

    # No active quiz for this token: either it was already saved (repeat submit) or it expired.
    if not state or state["token"] != token:
        return _redirect_to_saved_attempt(token)

    taken = int(time.time()) - state["started"]
    if taken > state["limit"] + GRACE_SECONDS:
        session.pop("quiz", None)
        flash("Time was up before your answers were submitted, so this attempt was not saved.", "warning")
        return redirect(url_for("aptitude.index"))

    selected = {}
    for qid in state["ids"]:
        raw = request.form.get(f"q_{qid}", "")
        if raw == "":
            selected[qid] = None
        elif raw in ("1", "2", "3", "4"):
            selected[qid] = int(raw)
        else:
            flash("One of your answers was invalid. Please review and submit again.", "danger")
            return redirect(url_for("aptitude.quiz"))

    questions = Question.query.filter(Question.id.in_(state["ids"])).all()
    order = {qid: n for n, qid in enumerate(state["ids"])}
    questions.sort(key=lambda q: order[q.id])
    correct = sum(1 for q in questions if selected[q.id] == q.correct_option)

    result = QuizResult(user_id=current_user.id, subject=state["category"],
                        total_questions=len(questions), correct_answers=correct)
    attempt = AptitudeAttempt(token=token, user_id=current_user.id, result=result,
                              category=state["category"], difficulty=state["difficulty"],
                              time_taken=min(taken, state["limit"]))
    for q in questions:
        attempt.answers.append(AttemptAnswer(
            question_id=q.id, selected_option=selected[q.id],
            is_correct=selected[q.id] == q.correct_option))
    db.session.add(attempt)
    try:
        db.session.commit()
    except IntegrityError:  # a concurrent duplicate submit won the race
        db.session.rollback()
        return _redirect_to_saved_attempt(token)

    session.pop("quiz", None)
    return redirect(url_for("aptitude.result", attempt_id=attempt.id))


def _redirect_to_saved_attempt(token):
    existing = AptitudeAttempt.query.filter_by(token=token, user_id=current_user.id).first() if token else None
    if existing:
        return redirect(url_for("aptitude.result", attempt_id=existing.id))
    flash("That quiz is no longer active. Please start a new one.", "warning")
    return redirect(url_for("aptitude.index"))


@aptitude.route("/result/<int:attempt_id>")
@student_required
def result(attempt_id):
    attempt = AptitudeAttempt.query.filter_by(id=attempt_id, user_id=current_user.id).first()
    if attempt is None:
        abort(404)
    r = attempt.result
    return render_template("aptitude/result.html", attempt=attempt, result=r,
                           unanswered=sum(1 for a in attempt.answers if a.selected_option is None))
