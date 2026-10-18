import os

from flask import Flask, render_template

from config import Config
from app.extensions import csrf, db, login_manager
from app.interview_seed import seed_interview_questions
from app.schema import upgrade_schema
from app.seed_data import seed_questions
from app.sql_engine import ensure_practice_db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401  (register models before create_all)
    from app.auth import auth
    from app.aptitude import aptitude
    from app.sql_lab import sql_lab
    from app.python_lab import python_lab
    from app.interview import interview
    from app.progress import progress
    from app.admin import admin
    from app.routes import main
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(aptitude)
    app.register_blueprint(sql_lab)
    app.register_blueprint(python_lab)
    app.register_blueprint(interview)
    app.register_blueprint(progress)
    app.register_blueprint(admin)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    @app.errorhandler(400)
    def bad_request(_):
        return render_template("error.html", code=400,
                               message="That request could not be processed. If a form expired, go back and try again."), 400

    @app.errorhandler(405)
    def not_allowed(_):
        return render_template("error.html", code=405, message="That action is not allowed here."), 405

    @app.errorhandler(500)
    def server_error(_):
        db.session.rollback()
        return render_template("error.html", code=500, message="Something went wrong on our side."), 500

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", code=403, message="You don't have access to this page."), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="Page not found."), 404

    with app.app_context():
        upgrade_schema(db.engine)
        db.create_all()
        seed_questions()
        seed_interview_questions()
        ensure_practice_db(app.config["SQL_PRACTICE_DB"])

    return app
