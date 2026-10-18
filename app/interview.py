import json
import random
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app import llm
from app.auth import student_required
from app.extensions import db
from app.interview_seed import HR_CATEGORIES, TECHNICAL_CATEGORIES
from app.models import InterviewQuestion, InterviewResponse, MockAnswer, MockSession

interview = Blueprint("interview", __name__, url_prefix="/interview")

DIFFICULTIES = ["Easy", "Medium", "Hard"]
MAX_RESPONSE_LENGTH = 3000
MAX_SEARCH_LENGTH = 100

KINDS = {
    "technical": {"label": "Technical Interview", "icon": "bi-cpu", "categories": TECHNICAL_CATEGORIES,
                  "text": "Python, SQL, OOP, DSA, web development, databases and software engineering."},
    "hr": {"label": "HR Interview", "icon": "bi-people", "categories": HR_CATEGORIES,
           "text": "Self-introduction, strengths, projects, teamwork and why you should be hired."},
}


def _saved_question_ids(kind=None):
    query = (db.session.query(InterviewResponse.question_id)
             .filter(InterviewResponse.user_id == current_user.id))
    if kind:
        query = query.join(InterviewQuestion, InterviewQuestion.id == InterviewResponse.question_id) \
                     .filter(InterviewQuestion.kind == kind)
    return {row[0] for row in query.all()}


@interview.route("/")
@student_required
def index():
    cards = []
    for key, info in KINDS.items():
        total = InterviewQuestion.query.filter_by(kind=key).count()
        cards.append({"key": key, "total": total, "answered": len(_saved_question_ids(key)), **info})
    return render_template("interview/index.html", cards=cards)


@interview.route("/<any(technical, hr):kind>")
@student_required
def question_list(kind):
    info = KINDS[kind]
    category = request.args.get("category", "")
    difficulty = request.args.get("difficulty", "")
    term = request.args.get("q", "").strip()[:MAX_SEARCH_LENGTH]
    # Ignore filter values that are not valid choices
    if category not in info["categories"]:
        category = ""
    if difficulty not in DIFFICULTIES:
        difficulty = ""

    query = InterviewQuestion.query.filter_by(kind=kind)
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if term:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        query = query.filter(or_(InterviewQuestion.text.ilike(like, escape="\\"),
                                 InterviewQuestion.key_concepts.ilike(like, escape="\\"),
                                 InterviewQuestion.category.ilike(like, escape="\\")))
    questions = query.order_by(InterviewQuestion.id).all()
    return render_template("interview/list.html", kind=kind, info=info, questions=questions,
                           category=category, difficulty=difficulty, term=term,
                           difficulties=DIFFICULTIES, answered=_saved_question_ids(kind))


def _get_question_or_404(question_id):
    q = db.session.get(InterviewQuestion, question_id)
    if q is None:
        abort(404)
    return q


def _my_response(question_id):
    return InterviewResponse.query.filter_by(user_id=current_user.id, question_id=question_id).first()


@interview.route("/question/<int:question_id>", methods=["GET", "POST"])
@student_required
def question(question_id):
    q = _get_question_or_404(question_id)
    saved = _my_response(question_id)
    text = saved.response_text if saved else ""
    error = None

    if request.method == "POST":
        text = request.form.get("response", "").strip()
        if not text:
            error = "Please write your answer before saving."
        elif len(text) > MAX_RESPONSE_LENGTH:
            error = f"Your answer is too long (maximum {MAX_RESPONSE_LENGTH} characters)."
        else:
            now = datetime.now(timezone.utc)
            if saved:
                saved.response_text, saved.updated_at = text, now
            else:
                db.session.add(InterviewResponse(user_id=current_user.id, question_id=question_id,
                                                 response_text=text, created_at=now, updated_at=now))
            try:
                db.session.commit()
            except IntegrityError:  # double-submit race: the other request already created it
                db.session.rollback()
                saved = _my_response(question_id)
                saved.response_text, saved.updated_at = text, now
                db.session.commit()
            flash("Your answer has been saved.", "success")
            return redirect(url_for("interview.question", question_id=question_id))

    return render_template("interview/question.html", q=q, saved=saved, text=text, error=error,
                           max_len=MAX_RESPONSE_LENGTH, kind_info=KINDS[q.kind])


@interview.route("/question/<int:question_id>/delete", methods=["POST"])
@student_required
def delete_response(question_id):
    q = _get_question_or_404(question_id)
    saved = _my_response(question_id)  # scoped to the logged-in student
    if saved:
        db.session.delete(saved)
        db.session.commit()
        flash("Your saved answer was deleted.", "info")
    return redirect(url_for("interview.question", question_id=q.id))


# ---------------------------------------------------------------- AI Mock Interview
MOCK_TOPICS = TECHNICAL_CATEGORIES + HR_CATEGORIES
MOCK_COUNTS = [3, 4, 5]
MAX_MOCK_ANSWER_LENGTH = 1500  # keeps prompts (and token cost) small
MAX_ACTIVE_SESSIONS = 3  # unfinished sessions per student
FALLBACK_REASONS = {
    "no_key": "No AI service is configured on this server.",
    "limit": "Your daily AI feedback limit has been reached.",
}


def _ai_calls_today():
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return (MockAnswer.query.join(MockSession, MockSession.id == MockAnswer.session_id)
            .filter(MockSession.user_id == current_user.id, MockAnswer.source == "ai",
                    MockAnswer.created_at >= since).count())


def _get_session_or_404(session_id):
    ms = db.session.get(MockSession, session_id)
    if ms is None or ms.user_id != current_user.id:  # other students' sessions look like 404s
        abort(404)
    return ms


def _questions_by_id(ms):
    found = {q.id: q for q in InterviewQuestion.query.filter(InterviewQuestion.id.in_(ms.ids)).all()}
    return [found[i] for i in ms.ids if i in found]


@interview.route("/mock")
@student_required
def mock_index():
    recent = (MockSession.query.filter_by(user_id=current_user.id)
              .order_by(MockSession.id.desc()).limit(10).all())
    return render_template("interview/mock_index.html", topics=MOCK_TOPICS, difficulties=DIFFICULTIES,
                           counts=MOCK_COUNTS, recent=recent, ai_on=llm.is_configured(current_app.config))


@interview.route("/mock/start", methods=["POST"])
@student_required
def mock_start():
    topic = request.form.get("topic", "")
    difficulty = request.form.get("difficulty", "")
    try:
        count = int(request.form.get("count", ""))
    except ValueError:
        count = 0
    if topic not in MOCK_TOPICS or difficulty not in DIFFICULTIES or count not in MOCK_COUNTS:
        flash("Please choose a topic, difficulty and number of questions from the lists.", "danger")
        return redirect(url_for("interview.mock_index"))

    active = MockSession.query.filter_by(user_id=current_user.id, completed_at=None).count()
    if active >= MAX_ACTIVE_SESSIONS:
        flash("You have several unfinished interviews. Finish one before starting another.", "warning")
        return redirect(url_for("interview.mock_index"))

    # Difficulty is a preference: nearest levels first, so a topic with no questions at that level still works
    pool = InterviewQuestion.query.filter_by(category=topic).all()
    if not pool:
        flash(f"No questions are available for {topic} yet.", "warning")
        return redirect(url_for("interview.mock_index"))
    want = DIFFICULTIES.index(difficulty)
    random.shuffle(pool)
    pool.sort(key=lambda q: abs(DIFFICULTIES.index(q.difficulty) - want))
    chosen = pool[:count]
    if len(chosen) < count:
        flash(f"Only {len(chosen)} {topic} question{'' if len(chosen) == 1 else 's'} available, "
              "so this interview is shorter.", "info")

    ms = MockSession(user_id=current_user.id, topic=topic, difficulty=difficulty,
                     mode="ai" if llm.is_configured(current_app.config) else "fallback",
                     question_ids=",".join(str(q.id) for q in chosen))
    db.session.add(ms)
    db.session.commit()
    return redirect(url_for("interview.mock_session", session_id=ms.id))


@interview.route("/mock/<int:session_id>")
@student_required
def mock_session(session_id):
    ms = _get_session_or_404(session_id)
    questions = _questions_by_id(ms)
    position = len(ms.answers)
    if position >= len(questions):
        return redirect(url_for("interview.mock_summary", session_id=ms.id))
    return render_template("interview/mock_question.html", ms=ms, q=questions[position], position=position,
                           total=len(questions), max_len=MAX_MOCK_ANSWER_LENGTH, text="", error=None)


@interview.route("/mock/<int:session_id>/answer", methods=["POST"])
@student_required
def mock_answer(session_id):
    ms = _get_session_or_404(session_id)
    questions = _questions_by_id(ms)
    position = len(ms.answers)
    if position >= len(questions):
        return redirect(url_for("interview.mock_summary", session_id=ms.id))
    q = questions[position]

    text = request.form.get("response", "").strip()
    error = None
    if not text:
        error = "Please write your answer before submitting."
    elif len(text) > MAX_MOCK_ANSWER_LENGTH:
        error = f"Your answer is too long (maximum {MAX_MOCK_ANSWER_LENGTH} characters)."
    if error:
        return render_template("interview/mock_question.html", ms=ms, q=q, position=position, total=len(questions),
                               max_len=MAX_MOCK_ANSWER_LENGTH, text=text, error=error), 400

    config = current_app.config
    source, reason, feedback = "fallback", None, None
    if not llm.is_configured(config):
        reason = "no_key"
    elif _ai_calls_today() >= config["LLM_DAILY_LIMIT_PER_USER"]:
        reason = "limit"
    else:
        try:
            feedback = llm.ai_feedback(config, q, text)
            source = "ai"
        except llm.LLMError as exc:
            current_app.logger.warning("LLM feedback failed: %s", exc)
            reason = str(exc)[:100]
    if feedback is None:
        feedback = llm.fallback_feedback(q, text)

    db.session.add(MockAnswer(session_id=ms.id, position=position, question_id=q.id, answer_text=text,
                              source=source, fallback_reason=reason, feedback_json=json.dumps(feedback)))
    if position + 1 >= len(questions):
        ms.completed_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
    except IntegrityError:  # double submit: the first request already saved this question
        db.session.rollback()
    return redirect(url_for("interview.mock_feedback", session_id=ms.id, position=position))


@interview.route("/mock/<int:session_id>/feedback/<int:position>")
@student_required
def mock_feedback(session_id, position):
    ms = _get_session_or_404(session_id)
    answer = next((a for a in ms.answers if a.position == position), None)
    if answer is None:
        abort(404)
    total = len(ms.ids)
    return render_template("interview/mock_feedback.html", ms=ms, a=answer, fb=json.loads(answer.feedback_json),
                           total=total, is_last=position + 1 >= total,
                           reason_text=FALLBACK_REASONS.get(answer.fallback_reason, answer.fallback_reason))


@interview.route("/mock/<int:session_id>/summary")
@student_required
def mock_summary(session_id):
    ms = _get_session_or_404(session_id)
    items = [(a, json.loads(a.feedback_json)) for a in ms.answers]
    scored = [fb["scores"] for a, fb in items if a.source == "ai" and fb.get("scores")]
    averages = {m: round(sum(s[m] for s in scored) / len(scored), 1) for m in llm.METRICS} if scored else {}
    return render_template("interview/mock_summary.html", ms=ms, items=items, averages=averages,
                           scored_count=len(scored), total=len(ms.ids))
