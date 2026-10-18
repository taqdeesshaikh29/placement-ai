import click
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.admin_forms import AptitudeQuestionForm, InterviewQuestionForm
from app.auth import admin_required
from app.extensions import db
from app.models import (AttemptAnswer, InterviewQuestion, InterviewResponse, MockAnswer, MockSession, Question,
                        User)

admin = Blueprint("admin", __name__, url_prefix="/admin")
PER_PAGE = 25

KINDS = {
    "aptitude": {"label": "Aptitude questions", "model": Question, "form": AptitudeQuestionForm},
    "interview": {"label": "Interview questions", "model": InterviewQuestion, "form": InterviewQuestionForm},
}


@admin.cli.command("promote")
@click.argument("email")
def promote(email):
    """Give an existing account the admin role: flask --app run admin promote EMAIL"""
    user = User.query.filter_by(email=email.strip().lower()).first()
    if user is None:
        raise click.ClickException("No account with that email. Register it first.")
    user.role = "admin"
    db.session.commit()
    click.echo(f"{user.email} is now an administrator.")


def _kind(kind):
    info = KINDS.get(kind)
    if info is None:
        abort(404)
    return info


def _get_or_404(info, qid):
    obj = db.session.get(info["model"], qid)
    if obj is None:
        abort(404)
    return obj


def _usage(kind, obj):
    """How many saved student records point at this question (non-zero blocks deletion)."""
    if kind == "aptitude":
        return AttemptAnswer.query.filter_by(question_id=obj.id).count()
    count = (InterviewResponse.query.filter_by(question_id=obj.id).count()
             + MockAnswer.query.filter_by(question_id=obj.id).count())
    for ms in MockSession.query.filter(MockSession.completed_at.is_(None)):  # unfinished interviews still need it
        if obj.id in ms.ids:
            count += 1
    return count


@admin.route("/")
@admin_required
def index():
    cards = [{"kind": k, "label": i["label"], "total": i["model"].query.count()} for k, i in KINDS.items()]
    return render_template("admin/index.html", cards=cards)


@admin.route("/<kind>")
@admin_required
def question_list(kind):
    info = _kind(kind)
    model = info["model"]
    category = request.args.get("category", "")
    query = model.query
    if category:
        query = query.filter_by(category=category)
    page = query.order_by(model.id).paginate(page=request.args.get("page", 1, type=int), per_page=PER_PAGE,
                                             error_out=False)
    categories = [c for (c,) in db.session.query(model.category).distinct().order_by(model.category)]
    return render_template("admin/list.html", kind=kind, info=info, page=page, category=category,
                           categories=categories)


def _fill(kind, obj, form):
    if kind == "aptitude":
        form.populate_obj(obj)
        return
    obj.kind, obj.category, obj.difficulty = form.kind.data, form.category.data, form.difficulty.data
    obj.text, obj.sample_answer = form.text.data.strip(), form.sample_answer.data.strip()
    obj.key_concepts = "|".join(form.concept_list(form.key_concepts.data))


@admin.route("/<kind>/new", methods=["GET", "POST"])
@admin_required
def question_new(kind):
    info = _kind(kind)
    form = info["form"]()
    if form.validate_on_submit():
        obj = info["model"]()
        _fill(kind, obj, form)
        db.session.add(obj)
        db.session.commit()
        flash("Question created.", "success")
        return redirect(url_for("admin.question_list", kind=kind))
    return render_template("admin/form.html", kind=kind, info=info, form=form, obj=None, locked=False)


@admin.route("/<kind>/<int:qid>/edit", methods=["GET", "POST"])
@admin_required
def question_edit(kind, qid):
    info = _kind(kind)
    obj = _get_or_404(info, qid)
    form = info["form"](obj=obj)
    if kind == "interview" and request.method == "GET":
        form.key_concepts.data = "\n".join(obj.concepts)
    # Once students have answered an aptitude question, its answer key is frozen so their saved
    # correct/incorrect results stay true. Wording and explanation can still be edited.
    locked = kind == "aptitude" and _usage(kind, obj) > 0
    if form.validate_on_submit():
        if locked and any(getattr(form, f).data != getattr(obj, f) for f in AptitudeQuestionForm.ANSWER_FIELDS):
            form.correct_option.errors.append(
                "Students have already answered this question, so its options and correct answer cannot change. "
                "Create a new question instead.")
        else:
            _fill(kind, obj, form)
            db.session.commit()
            flash("Question updated.", "success")
            return redirect(url_for("admin.question_list", kind=kind))
    return render_template("admin/form.html", kind=kind, info=info, form=form, obj=obj, locked=locked)


@admin.route("/<kind>/<int:qid>/delete", methods=["POST"])
@admin_required
def question_delete(kind, qid):
    info = _kind(kind)
    obj = _get_or_404(info, qid)
    if _usage(kind, obj):
        flash("This question cannot be deleted because student records refer to it. Edit it instead.", "danger")
    else:
        db.session.delete(obj)
        db.session.commit()
        flash("Question deleted.", "info")
    return redirect(url_for("admin.question_list", kind=kind))
