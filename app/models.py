from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_student(self):
        return self.role == "student"

    @property
    def is_admin(self):
        return self.role == "admin"


class QuizResult(db.Model):
    """One completed quiz/practice session for a student."""
    __tablename__ = "quiz_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject = db.Column(db.String(50), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("quiz_results", lazy="dynamic"))

    @property
    def accuracy(self):
        return round(100 * self.correct_answers / self.total_questions) if self.total_questions else 0


class Question(db.Model):
    """A multiple-choice aptitude question with four options."""
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    difficulty = db.Column(db.String(10), nullable=False, index=True)  # Easy / Medium / Hard
    text = db.Column(db.Text, nullable=False)
    option_1 = db.Column(db.String(255), nullable=False)
    option_2 = db.Column(db.String(255), nullable=False)
    option_3 = db.Column(db.String(255), nullable=False)
    option_4 = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)  # 1-4
    explanation = db.Column(db.Text, nullable=False)

    @property
    def options(self):
        return [self.option_1, self.option_2, self.option_3, self.option_4]


class AptitudeAttempt(db.Model):
    """A submitted aptitude quiz. Its token is unique, so a quiz can be saved only once."""
    __tablename__ = "aptitude_attempts"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    result_id = db.Column(db.Integer, db.ForeignKey("quiz_results.id"), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(10), nullable=False)  # Easy / Medium / Hard / Mixed
    time_taken = db.Column(db.Integer, nullable=False)  # seconds

    result = db.relationship("QuizResult")
    answers = db.relationship("AttemptAnswer", backref="attempt", order_by="AttemptAnswer.id")


class AttemptAnswer(db.Model):
    __tablename__ = "attempt_answers"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("aptitude_attempts.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    selected_option = db.Column(db.Integer, nullable=True)  # None = unanswered
    is_correct = db.Column(db.Boolean, nullable=False)

    question = db.relationship("Question")


class SqlAttempt(db.Model):
    """A student's checked answer in the SQL Lab (only checked answers are saved)."""
    __tablename__ = "sql_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, nullable=False, index=True)
    query_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    error = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))


class PythonAttempt(db.Model):
    """A submitted answer in the Python Practice module."""
    __tablename__ = "python_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, nullable=False, index=True)
    answer_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))


class InterviewQuestion(db.Model):
    """A technical or HR interview question with key concepts and a sample answer."""
    __tablename__ = "interview_questions"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(10), nullable=False, index=True)  # "technical" or "hr"
    category = db.Column(db.String(50), nullable=False, index=True)
    difficulty = db.Column(db.String(10), nullable=False)  # Easy / Medium / Hard
    text = db.Column(db.Text, nullable=False)
    key_concepts = db.Column(db.Text, nullable=False)  # "|"-separated
    sample_answer = db.Column(db.Text, nullable=False)

    @property
    def concepts(self):
        return [c for c in self.key_concepts.split("|") if c]


class InterviewResponse(db.Model):
    """A student's own written answer. One per student per question (editable)."""
    __tablename__ = "interview_responses"
    __table_args__ = (db.UniqueConstraint("user_id", "question_id", name="uq_response_user_question"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("interview_questions.id"), nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    question = db.relationship("InterviewQuestion")


class MockSession(db.Model):
    """One AI Mock Interview run: a topic, a difficulty and a fixed list of questions."""
    __tablename__ = "mock_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    topic = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(10), nullable=False)
    mode = db.Column(db.String(10), nullable=False)  # "ai" or "fallback" when the session started
    question_ids = db.Column(db.String(100), nullable=False)  # comma-separated InterviewQuestion ids, in order
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    answers = db.relationship("MockAnswer", backref="session", order_by="MockAnswer.position",
                              cascade="all, delete-orphan")

    @property
    def ids(self):
        return [int(i) for i in self.question_ids.split(",") if i]


class MockAnswer(db.Model):
    """A student's answer within a mock session, with the feedback they received."""
    __tablename__ = "mock_answers"
    __table_args__ = (db.UniqueConstraint("session_id", "position", name="uq_mock_answer_position"),)

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("mock_sessions.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)  # 0-based index into the session's questions
    question_id = db.Column(db.Integer, db.ForeignKey("interview_questions.id"), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(10), nullable=False)  # "ai" or "fallback" - who produced the feedback
    fallback_reason = db.Column(db.String(100), nullable=True)
    feedback_json = db.Column(db.Text, nullable=False)  # compact JSON, see app/llm.py
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    question = db.relationship("InterviewQuestion")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
