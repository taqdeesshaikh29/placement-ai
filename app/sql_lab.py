from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user

from app.auth import student_required
from app.extensions import db
from app.models import SqlAttempt
from app.sql_engine import (MAX_CHECK_ROWS, MAX_DISPLAY_ROWS, MAX_SQL_LENGTH, SqlLabError,
                            compare_results, describe_tables, run_query)
from app.sql_questions import QUESTIONS, TOPICS, get_question

sql_lab = Blueprint("sql_lab", __name__, url_prefix="/sql-lab")


def _db_path():
    return current_app.config["SQL_PRACTICE_DB"]


def _progress(user_id):
    """Per-student summary built from saved attempts."""
    attempts = SqlAttempt.query.filter_by(user_id=user_id).all()
    solved = {a.question_id for a in attempts if a.is_correct}
    return {
        "solved_ids": solved,
        "solved": len(solved),
        "total": len(QUESTIONS),
        "attempts": len(attempts),
        "percent": round(100 * len(solved) / len(QUESTIONS)),
    }


@sql_lab.route("/")
@student_required
def index():
    grouped = [(t, [q for q in QUESTIONS if q["topic"] == t]) for t in TOPICS]
    return render_template("sql_lab/index.html", grouped=grouped, progress=_progress(current_user.id),
                           tables=describe_tables(_db_path()))


@sql_lab.route("/question/<int:qid>", methods=["GET", "POST"])
@student_required
def question(qid):
    q = get_question(qid)
    if q is None:
        abort(404)

    context = {"q": q, "query": "", "result": None, "error": None, "feedback": None,
               "correct": False, "max_len": MAX_SQL_LENGTH, "display_rows": MAX_DISPLAY_ROWS}

    if request.method == "POST":
        action = request.form.get("action", "run")
        query = request.form.get("query", "")
        context["query"] = query
        if action not in ("run", "check"):
            abort(400)

        try:
            result = run_query(_db_path(), query, max_rows=MAX_CHECK_ROWS)
        except SqlLabError as exc:
            context["error"] = str(exc)
            result = None

        if result is not None:
            if action == "check":
                expected = run_query(_db_path(), q["answer_sql"], max_rows=MAX_CHECK_ROWS)
                ok, message = compare_results(expected, result, q["ordered"])
                context["correct"], context["feedback"] = ok, message
            context["result"] = result

        if action == "check":
            db.session.add(SqlAttempt(
                user_id=current_user.id, question_id=qid, query_text=query.strip()[:MAX_SQL_LENGTH],
                is_correct=context["correct"], error=(context["error"] or "")[:255] or None))
            db.session.commit()

    context["progress"] = _progress(current_user.id)
    context["solved_before"] = qid in context["progress"]["solved_ids"]
    context["tables"] = describe_tables(_db_path())
    context["next_q"] = get_question(qid + 1)
    return render_template("sql_lab/question.html", **context)
