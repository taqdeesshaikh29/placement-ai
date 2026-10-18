import time
from functools import wraps
from urllib.parse import urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms import LoginForm, RegisterForm
from app.models import User

auth = Blueprint("auth", __name__)

# Login throttle: too many failures for one email from one address pauses further attempts.
# Kept in memory, so it resets on restart and is per process (fine for a single-server deployment).
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300
_failed_logins = {}  # (ip, email) -> [timestamps]


def _throttle_key(email):
    return (request.remote_addr, email)


def _is_locked(key):
    now = time.time()
    recent = [t for t in _failed_logins.get(key, []) if now - t < LOCKOUT_SECONDS]
    if recent:
        _failed_logins[key] = recent
    else:
        _failed_logins.pop(key, None)
    return len(recent) >= MAX_FAILED_LOGINS


def student_required(view):
    """Allow only logged-in users with the student role."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_student:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Allow only logged-in administrators. Checked on the server for every admin route."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _home(user):
    return url_for("admin.index" if user.is_admin else "main.dashboard")


def _safe_next(target):
    """Only allow relative redirects within this site."""
    # Browsers treat a backslash like a slash, so "/\\evil.com" would leave the site.
    if (target and target.startswith("/") and not target.startswith("//") and "\\" not in target
            and not urlparse(target).netloc):
        return target
    return None


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(_home(current_user))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(),
                    email=form.email.data.strip().lower(),
                    role="student")
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:  # race: email taken between validation and insert
            db.session.rollback()
            form.email.errors.append("An account with this email already exists.")
        else:
            flash("Account created! Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_home(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        key = _throttle_key(email)
        if _is_locked(key):
            flash("Too many failed attempts. Please wait a few minutes and try again.", "danger")
            return render_template("auth/login.html", form=form), 429
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            _failed_logins.pop(key, None)
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(_safe_next(request.args.get("next")) or _home(user))
        _failed_logins.setdefault(key, []).append(time.time())
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", form=form)


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
