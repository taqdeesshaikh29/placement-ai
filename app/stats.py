import json

from sqlalchemy import case, func

from app.extensions import db
from app.models import (AptitudeAttempt, AttemptAnswer, InterviewQuestion, InterviewResponse, MockAnswer,
                        MockSession, PythonAttempt, QuizResult, SqlAttempt)
from app.python_questions import POINTS, QUESTIONS as PY_QUESTIONS, get_question as get_py_question
from app.sql_questions import get_question as get_sql_question


def _pct(correct, total):
    return round(100 * correct / total) if total else 0


def get_python_progress(user_id):
    """Python Practice summary for one student, from their saved attempts."""
    attempts = PythonAttempt.query.filter_by(user_id=user_id).all()
    solved = {a.question_id for a in attempts if a.is_correct}
    by_id = {q["id"]: q for q in PY_QUESTIONS}
    return {
        "solved_ids": solved,
        "solved": len(solved),
        "total": len(PY_QUESTIONS),
        "points": sum(POINTS[by_id[i]["difficulty"]] for i in solved if i in by_id),
        "max_points": sum(POINTS[q["difficulty"]] for q in PY_QUESTIONS),
        "attempts": len(attempts),
        "correct_attempts": sum(1 for a in attempts if a.is_correct),
    }


def get_subject_stats(user_id):
    """Per-subject totals for one student: aptitude categories, plus Python and SQL practice.

    Each saved quiz counts its questions; each submitted Python/SQL answer counts as one attempt.
    """
    rows = (
        db.session.query(
            QuizResult.subject,
            func.sum(QuizResult.total_questions),
            func.sum(QuizResult.correct_answers),
        )
        .filter(QuizResult.user_id == user_id)
        .group_by(QuizResult.subject)
        .all()
    )
    subjects = [(s, int(t), int(c)) for s, t, c in rows]
    for name, model in (("Python", PythonAttempt), ("SQL", SqlAttempt)):
        total, correct = (db.session.query(func.count(model.id),
                                           func.coalesce(func.sum(case((model.is_correct.is_(True), 1), else_=0)), 0))
                          .filter(model.user_id == user_id).one())
        if total:
            subjects.append((name, int(total), int(correct)))
    return [{"subject": s, "attempted": t, "correct": c, "accuracy": _pct(c, t)}
            for s, t, c in sorted(subjects)]


def get_dashboard_stats(user):
    """Compute dashboard numbers from this user's saved records only."""
    subjects = get_subject_stats(user.id)
    python = get_python_progress(user.id)

    attempted = sum(s["attempted"] for s in subjects)
    correct = sum(s["correct"] for s in subjects)

    recent = (
        user.quiz_results
        .order_by(QuizResult.created_at.desc(), QuizResult.id.desc())
        .limit(5)
        .all()
    )

    return {
        "attempted": attempted,
        "accuracy": _pct(correct, attempted),
        "quiz_count": user.quiz_results.count(),
        "subjects": subjects,
        "recent": recent,
        "python": python,
        "recommendation": _recommend(subjects),
    }


def _recommend(subjects):
    """Suggest practising the weakest subject; fall back to getting started."""
    if not subjects:
        return {"title": "Take your first quiz",
                "text": "Complete a practice quiz to unlock your performance insights.",
                "endpoint": "aptitude.index"}
    weakest = min(subjects, key=lambda s: (s["accuracy"], -s["attempted"]))
    return {"title": f"Practice {weakest['subject']}",
            "text": f"Your accuracy in {weakest['subject']} is {weakest['accuracy']}%, "
                    "your lowest subject. A focused session will help the most.",
            "endpoint": {"Python": "python_lab.index", "SQL": "sql_lab.index"}.get(weakest["subject"], "aptitude.index")}


# ---------------------------------------------------------------- Progress tracking
def get_quiz_trend(user_id, limit=20):
    """The student's last `limit` aptitude quiz scores, oldest first, for the score-over-time chart."""
    rows = (QuizResult.query.filter_by(user_id=user_id)
            .order_by(QuizResult.created_at.desc(), QuizResult.id.desc()).limit(limit).all())
    return [{"label": r.created_at.strftime("%d %b"), "subject": r.subject, "accuracy": r.accuracy,
             "correct": r.correct_answers, "total": r.total_questions} for r in reversed(rows)]


def _py_answer_text(q, raw):
    if q and q["type"] == "choice" and raw.isdigit() and int(raw) < len(q["options"]):
        return q["options"][int(raw)]
    return raw


def get_practice_history(user_id, limit=30):
    """Newest-first mix of quizzes, Python answers and SQL answers, each with a link target."""
    items = []
    for at in (AptitudeAttempt.query.filter_by(user_id=user_id).join(QuizResult, AptitudeAttempt.result)
               .order_by(QuizResult.created_at.desc()).limit(limit)):
        r = at.result
        items.append({"when": r.created_at, "kind": "Aptitude quiz", "title": f"{at.category} · {at.difficulty}",
                      "result": f"{r.correct_answers}/{r.total_questions} ({r.accuracy}%)",
                      "ok": r.accuracy >= 60, "endpoint": "aptitude.result", "args": {"attempt_id": at.id}})
    for model, kind, getter, endpoint in ((PythonAttempt, "Python", get_py_question, "python_lab.question"),
                                          (SqlAttempt, "SQL", get_sql_question, "sql_lab.question")):
        for a in model.query.filter_by(user_id=user_id).order_by(model.created_at.desc()).limit(limit):
            q = getter(a.question_id)
            items.append({"when": a.created_at, "kind": f"{kind} practice",
                          "title": q["title"] if q else f"Question {a.question_id}",
                          "result": "Correct" if a.is_correct else "Incorrect", "ok": a.is_correct,
                          "endpoint": endpoint if q else None, "args": {"qid": a.question_id}})
    items.sort(key=lambda i: i["when"], reverse=True)
    return items[:limit]


def get_incorrect_answers(user_id, subject="", limit=50):
    """Wrong or unanswered answers for review. `subject` filters to one subject (blank = all)."""
    items = []
    if subject not in ("Python", "SQL"):
        query = (AttemptAnswer.query.join(AptitudeAttempt).join(QuizResult, AptitudeAttempt.result)
                 .filter(AptitudeAttempt.user_id == user_id, AttemptAnswer.is_correct.is_(False)))
        if subject:
            query = query.filter(AptitudeAttempt.category == subject)
        for a in query.order_by(QuizResult.created_at.desc(), AttemptAnswer.id).limit(limit):
            items.append({"when": a.attempt.result.created_at, "subject": a.attempt.category, "kind": "aptitude",
                          "question": a.question, "selected": a.selected_option, "attempt_id": a.attempt_id})
    for name, model, getter in (("Python", PythonAttempt, get_py_question), ("SQL", SqlAttempt, get_sql_question)):
        if subject not in ("", name):
            continue
        solved = {r[0] for r in db.session.query(model.question_id)
                  .filter(model.user_id == user_id, model.is_correct.is_(True))}
        for a in (model.query.filter_by(user_id=user_id, is_correct=False)
                  .order_by(model.created_at.desc()).limit(limit)):
            q = getter(a.question_id)
            if q is None:
                continue
            text = a.answer_text if name == "Python" else a.query_text
            items.append({"when": a.created_at, "subject": name, "kind": name.lower(), "title": q["title"],
                          "answer": _py_answer_text(q, text) if name == "Python" else text,
                          "qid": a.question_id, "solved_since": a.question_id in solved})
    items.sort(key=lambda i: i["when"], reverse=True)
    return items[:limit]


def get_interview_history(user_id):
    """Saved practice answers plus mock-interview sessions for one student."""
    saved = (db.session.query(InterviewResponse, InterviewQuestion)
             .join(InterviewQuestion, InterviewQuestion.id == InterviewResponse.question_id)
             .filter(InterviewResponse.user_id == user_id)
             .order_by(InterviewResponse.updated_at.desc()).limit(10).all())
    sessions = []
    for ms in MockSession.query.filter_by(user_id=user_id).order_by(MockSession.id.desc()).limit(10):
        ai = [a for a in ms.answers if a.source == "ai"]
        scores = [json.loads(a.feedback_json).get("scores") for a in ai]
        scores = [sc for sc in scores if sc]
        avg = round(sum(sum(sc.values()) / len(sc) for sc in scores) / len(scores), 1) if scores else None
        sessions.append({"session": ms, "answered": len(ms.answers), "total": len(ms.ids),
                         "ai_count": len(ai), "avg_score": avg})
    return {
        "saved": [{"response": r, "question": q} for r, q in saved],
        "saved_count": InterviewResponse.query.filter_by(user_id=user_id).count(),
        "mock_sessions": sessions,
        "mock_count": MockSession.query.filter_by(user_id=user_id).count(),
        "mock_answers": (MockAnswer.query.join(MockSession).filter(MockSession.user_id == user_id).count()),
    }
