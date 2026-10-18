from flask import Blueprint, abort, render_template, request
from flask_login import current_user

from app.auth import student_required
from app.extensions import db
from app.models import PythonAttempt
from app.python_questions import (DIFFICULTIES, POINTS, QUESTIONS, TOPICS, check_answer,
                                  get_question, solution_text)
from app.stats import get_python_progress

python_lab = Blueprint("python_lab", __name__, url_prefix="/python-lab")

MAX_ANSWER_LENGTH = 500


@python_lab.route("/")
@student_required
def index():
    level = request.args.get("level", "")
    if level and level not in DIFFICULTIES:
        level = ""
    grouped = [(t, [q for q in QUESTIONS if q["topic"] == t and (not level or q["difficulty"] == level)])
               for t in TOPICS]
    return render_template("python_lab/index.html", grouped=grouped, level=level,
                           difficulties=DIFFICULTIES, points=POINTS,
                           progress=get_python_progress(current_user.id))


@python_lab.route("/question/<int:qid>", methods=["GET", "POST"])
@student_required
def question(qid):
    q = get_question(qid)
    if q is None:
        abort(404)

    answer, error, correct, submitted = "", None, False, False

    if request.method == "POST":
        answer = request.form.get("answer", "")
        if q["type"] == "choice":
            # must be a valid option index; anything else is rejected, not scored
            if answer not in [str(i) for i in range(len(q["options"]))]:
                error = "Please choose one of the options."
            else:
                correct = check_answer(q, int(answer))
        else:
            answer = answer.strip()
            if not answer:
                error = "Please type an answer before submitting."
            elif len(answer) > MAX_ANSWER_LENGTH:
                error = f"Your answer is too long (maximum {MAX_ANSWER_LENGTH} characters)."
            else:
                correct = check_answer(q, answer)

        if error is None:
            submitted = True
            db.session.add(PythonAttempt(user_id=current_user.id, question_id=qid,
                                         answer_text=answer, is_correct=correct))
            db.session.commit()

    progress = get_python_progress(current_user.id)
    has_attempt = PythonAttempt.query.filter_by(user_id=current_user.id, question_id=qid).first() is not None
    # The solution is revealed only once the student has submitted an answer to this question.
    reveal = submitted or has_attempt

    nxt = get_question(qid + 1)
    return render_template("python_lab/question.html", q=q, answer=answer, error=error, correct=correct,
                           submitted=submitted, reveal=reveal, progress=progress, next_q=nxt,
                           solution=solution_text(q) if reveal else None, points=POINTS,
                           solved_before=qid in progress["solved_ids"], max_len=MAX_ANSWER_LENGTH)
