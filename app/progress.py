from flask import Blueprint, render_template, request
from flask_login import current_user

from app.auth import student_required
from app.stats import (get_incorrect_answers, get_interview_history, get_practice_history, get_quiz_trend,
                       get_subject_stats)

progress = Blueprint("progress", __name__, url_prefix="/progress")

# Every query below is filtered by current_user.id. No route takes a user or record id,
# so a student cannot ask for anyone else's data.


@progress.route("/")
@student_required
def index():
    subjects = get_subject_stats(current_user.id)
    attempted = sum(s["attempted"] for s in subjects)
    correct = sum(s["correct"] for s in subjects)
    return render_template(
        "progress/index.html", subjects=subjects, trend=get_quiz_trend(current_user.id),
        history=get_practice_history(current_user.id), interview=get_interview_history(current_user.id),
        attempted=attempted, accuracy=round(100 * correct / attempted) if attempted else 0)


@progress.route("/review")
@student_required
def review():
    subject = request.args.get("subject", "")
    names = [s["subject"] for s in get_subject_stats(current_user.id)]
    if subject not in names:  # ignore unknown filter values
        subject = ""
    return render_template("progress/review.html", items=get_incorrect_answers(current_user.id, subject),
                           subject=subject, subjects=names)
