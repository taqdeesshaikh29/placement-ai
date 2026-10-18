"""Core feature tests: auth, aptitude quiz, SQL Lab, Python Practice, interview prep, error pages."""
import os
import sqlite3
import tempfile
import unittest

from app import auth, create_app
from app.extensions import db
from app.stats import get_practice_history, get_subject_stats
from app.models import (AptitudeAttempt, InterviewResponse, PythonAttempt, Question, QuizResult, SqlAttempt,
                        User)
from app.python_questions import QUESTIONS as PY_QUESTIONS
from app.sql_questions import QUESTIONS as SQL_QUESTIONS
from tests.test_mock_interview import Base, make_config

REG = {"name": "New Student", "email": "new@example.com", "password": "password123",
       "confirm_password": "password123"}


class AuthTests(Base):
    def setUp(self):
        super().setUp()
        auth._failed_logins.clear()
        self.anon = self.app.test_client()

    def test_landing_page_and_links(self):
        html = self.anon.get("/").get_data(as_text=True)
        self.assertIn("Aptitude Tests", html)
        self.assertNotIn("Resume Analyzer", html)  # only features that exist are advertised

    def test_register_creates_student_with_hashed_password(self):
        r = self.anon.post("/register", data=REG)
        self.assertTrue(r.headers["Location"].endswith("/login"))
        with self.app.app_context():
            u = User.query.filter_by(email="new@example.com").one()
            self.assertEqual(u.role, "student")
            self.assertNotIn("password123", u.password_hash)

    def test_register_validation(self):
        for bad in (dict(REG, password="short1", confirm_password="short1"),
                    dict(REG, password="allletters", confirm_password="allletters"),
                    dict(REG, confirm_password="different1"),
                    dict(REG, email="not-an-email"),
                    dict(REG, email="S@example.com")):  # duplicate, case-insensitive
            self.assertEqual(self.anon.post("/register", data=bad).status_code, 200)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 2)

    def test_login_logout(self):
        r = self.anon.post("/login", data={"email": "S@Example.com", "password": "password123"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.anon.get("/dashboard").status_code, 200)
        self.assertEqual(self.anon.get("/logout").status_code, 405)  # logout is POST-only
        self.anon.post("/logout")
        self.assertEqual(self.anon.get("/dashboard").status_code, 302)

    def test_wrong_password_rejected(self):
        r = self.anon.post("/login", data={"email": "s@example.com", "password": "nope"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Invalid email or password", r.get_data(as_text=True))

    def test_login_redirect_only_to_local_paths(self):
        for target, allowed in (("/progress/", True), ("https://evil.com", False), ("//evil.com", False),
                                ("/\\evil.com", False), ("/aptitude/", True)):
            c = self.app.test_client()
            r = c.post("/login?next=" + target, data={"email": "s@example.com", "password": "password123"})
            loc = r.headers["Location"]
            self.assertEqual(loc.endswith(target) if allowed else loc.endswith("/dashboard"), True, (target, loc))

    def test_login_throttle(self):
        for _ in range(auth.MAX_FAILED_LOGINS):
            self.anon.post("/login", data={"email": "s@example.com", "password": "bad"})
        r = self.anon.post("/login", data={"email": "s@example.com", "password": "password123"})
        self.assertEqual(r.status_code, 429)
        # a different account is not locked out
        ok = self.anon.post("/login", data={"email": "o@example.com", "password": "password123"})
        self.assertEqual(ok.status_code, 302)

    def test_protected_pages_require_login(self):
        for url in ("/dashboard", "/aptitude/", "/sql-lab/", "/python-lab/", "/interview/", "/interview/mock",
                    "/progress/"):
            r = self.anon.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login", r.headers["Location"])

    def test_error_pages_and_headers(self):
        r = self.anon.get("/nope")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.anon.post("/").status_code, 405)


class AptitudeTests(Base):
    def start_quiz(self):
        self.client.post("/aptitude/start", data={"category": "Quantitative Aptitude", "difficulty": "Mixed"})
        with self.client.session_transaction() as s:
            return dict(s["quiz"])

    def test_start_validation(self):
        r = self.client.post("/aptitude/start", data={"category": "Bogus", "difficulty": "Mixed"})
        self.assertTrue(r.headers["Location"].endswith("/aptitude/"))
        with self.client.session_transaction() as s:
            self.assertNotIn("quiz", s)

    def test_submit_scores_saves_and_is_idempotent(self):
        state = self.start_quiz()
        with self.app.app_context():
            answers = {f"q_{q.id}": q.correct_option for q in Question.query.filter(Question.id.in_(state["ids"]))}
        # answer all but one correctly, leave one wrong
        wrong_key = next(iter(answers))
        answers[wrong_key] = answers[wrong_key] % 4 + 1
        data = dict(answers, token=state["token"])
        r = self.client.post("/aptitude/submit", data=data)
        self.assertEqual(r.status_code, 302)
        again = self.client.post("/aptitude/submit", data=data)  # double submit
        self.assertEqual(again.headers["Location"], r.headers["Location"])
        with self.app.app_context():
            self.assertEqual(QuizResult.query.count(), 1)
            res = QuizResult.query.one()
            self.assertEqual((res.total_questions, res.correct_answers), (len(answers), len(answers) - 1))
            self.assertEqual(AptitudeAttempt.query.one().user_id, self.uid)
        page = self.client.get(r.headers["Location"]).get_data(as_text=True)
        self.assertIn("Review", page)

    def test_invalid_option_is_rejected_not_saved(self):
        state = self.start_quiz()
        qid = state["ids"][0]
        r = self.client.post("/aptitude/submit", data={"token": state["token"], f"q_{qid}": "9"})
        self.assertTrue(r.headers["Location"].endswith("/aptitude/quiz"))
        with self.app.app_context():
            self.assertEqual(QuizResult.query.count(), 0)

    def test_unanswered_counts_as_incorrect(self):
        state = self.start_quiz()
        self.client.post("/aptitude/submit", data={"token": state["token"]})
        with self.app.app_context():
            self.assertEqual(QuizResult.query.one().correct_answers, 0)

    def test_wrong_token_does_not_save(self):
        self.start_quiz()
        self.client.post("/aptitude/submit", data={"token": "forged"})
        with self.app.app_context():
            self.assertEqual(QuizResult.query.count(), 0)


class SqlLabTests(Base):
    def post(self, qid, query, action="run"):
        return self.client.post(f"/sql-lab/question/{qid}", data={"query": query, "action": action})

    def test_pages_load(self):
        self.assertEqual(self.client.get("/sql-lab/").status_code, 200)
        self.assertEqual(self.client.get("/sql-lab/question/1").status_code, 200)
        self.assertEqual(self.client.get("/sql-lab/question/9999").status_code, 404)

    def test_correct_answer_is_checked_and_saved(self):
        q = SQL_QUESTIONS[0]
        html = self.post(q["id"], q["answer_sql"], "check").get_data(as_text=True)
        self.assertIn("Correct!", html)
        with self.app.app_context():
            a = SqlAttempt.query.one()
            self.assertTrue(a.is_correct)
            self.assertEqual(a.user_id, self.uid)

    def test_wrong_answer_saved_as_incorrect(self):
        self.post(1, "SELECT name FROM students", "check")
        with self.app.app_context():
            self.assertFalse(SqlAttempt.query.one().is_correct)

    def test_run_does_not_save_an_attempt(self):
        self.post(1, "SELECT * FROM students", "run")
        with self.app.app_context():
            self.assertEqual(SqlAttempt.query.count(), 0)

    def test_write_and_dangerous_statements_are_blocked(self):
        for sql in ("DELETE FROM students", "DROP TABLE students", "INSERT INTO students VALUES (99,'x','x',1,1)",
                    "UPDATE students SET cgpa = 10", "ATTACH DATABASE 'x.db' AS x", "PRAGMA table_info(students)",
                    "SELECT 1; DROP TABLE students", "SELECT * FROM sqlite_master"):
            html = self.post(1, sql, "run").get_data(as_text=True)
            self.assertRegex(html, r"allowed|Only one SQL|SQL error|Only queries", sql)
        html = self.post(1, "SELECT COUNT(*) FROM students", "run").get_data(as_text=True)
        self.assertIn("12", html)  # the practice data is untouched

    def test_empty_and_long_queries(self):
        self.assertIn("type a query", self.post(1, "   ", "run").get_data(as_text=True))
        self.assertIn("too long", self.post(1, "SELECT 1 " + "-" * 3000, "run").get_data(as_text=True))

    def test_bad_action_is_400(self):
        self.assertEqual(self.post(1, "SELECT 1", "hack").status_code, 400)


class PythonLabTests(Base):
    def answer(self, q):
        if q["type"] == "choice":
            return str(q["accepted"][0])
        return q["accepted"][0]

    def test_pages_load(self):
        self.assertEqual(self.client.get("/python-lab/").status_code, 200)
        self.assertEqual(self.client.get("/python-lab/question/1").status_code, 200)
        self.assertEqual(self.client.get("/python-lab/question/9999").status_code, 404)

    def test_every_question_page_renders_and_accepts_its_own_answer(self):
        for q in PY_QUESTIONS:
            self.assertEqual(self.client.get(f"/python-lab/question/{q['id']}").status_code, 200, q["id"])
            r = self.client.post(f"/python-lab/question/{q['id']}", data={"answer": self.answer(q)})
            self.assertEqual(r.status_code, 200, q["id"])
        with self.app.app_context():
            self.assertEqual(PythonAttempt.query.filter_by(is_correct=True).count(), len(PY_QUESTIONS))

    def test_wrong_and_invalid_answers(self):
        self.client.post("/python-lab/question/1", data={"answer": "definitely wrong"})
        self.client.post("/python-lab/question/1", data={"answer": "   "})
        self.client.post("/python-lab/question/1", data={"answer": "x" * 5000})
        with self.app.app_context():
            attempts = PythonAttempt.query.all()
            self.assertEqual(len(attempts), 1)
            self.assertFalse(attempts[0].is_correct)
        choice = next(q for q in PY_QUESTIONS if q["type"] == "choice")
        self.client.post(f"/python-lab/question/{choice['id']}", data={"answer": "99"})
        with self.app.app_context():
            self.assertEqual(PythonAttempt.query.count(), 1)  # invalid option not scored

    def test_solution_hidden_until_attempt(self):
        q = next(q for q in PY_QUESTIONS if q.get("solution"))
        before = self.client.get(f"/python-lab/question/{q['id']}").get_data(as_text=True)
        self.assertNotIn(q["solution"], before)


class InterviewPrepTests(Base):
    def test_browse_save_update_delete(self):
        self.assertEqual(self.client.get("/interview/").status_code, 200)
        self.assertEqual(self.client.get("/interview/technical?category=Python&difficulty=Easy&q=list").status_code, 200)
        self.assertEqual(self.client.get("/interview/technical?q=%25_%5C").status_code, 200)  # LIKE wildcards are escaped
        self.assertEqual(self.client.get("/interview/question/1").status_code, 200)
        self.assertEqual(self.client.get("/interview/question/9999").status_code, 404)
        self.client.post("/interview/question/1", data={"response": "First draft"})
        self.client.post("/interview/question/1", data={"response": "Second draft"})
        with self.app.app_context():
            self.assertEqual(InterviewResponse.query.one().response_text, "Second draft")
        self.assertEqual(self.client.post("/interview/question/1", data={"response": " "}).status_code, 200)
        self.assertEqual(self.client.post("/interview/question/1", data={"response": "x" * 3001}).status_code, 200)
        self.client.post("/interview/question/1/delete")
        with self.app.app_context():
            self.assertEqual(InterviewResponse.query.count(), 0)

    def test_answers_are_private_per_student(self):
        self.client.post("/interview/question/1", data={"response": "private text"})
        other = self.app.test_client()
        self.login("o@example.com", other)
        self.assertNotIn("private text", other.get("/interview/question/1").get_data(as_text=True))
        other.post("/interview/question/1/delete")  # must not delete the first student's answer
        with self.app.app_context():
            self.assertEqual(InterviewResponse.query.count(), 1)


class LegacySchemaTests(unittest.TestCase):
    """Databases made by older versions had sql_attempts.query instead of query_text."""

    def test_old_column_is_renamed_and_rows_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.db")
            con = sqlite3.connect(path)
            con.execute("CREATE TABLE sql_attempts (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
                        "question_id INTEGER NOT NULL, query TEXT NOT NULL, is_correct BOOLEAN NOT NULL, "
                        "error VARCHAR(255), created_at DATETIME NOT NULL)")
            con.execute("INSERT INTO sql_attempts VALUES (1, 1, 1, 'SELECT 1', 0, NULL, '2026-01-01 00:00:00')")
            con.commit()
            con.close()
            app = create_app(make_config(tmp, SQLALCHEMY_DATABASE_URI="sqlite:///" + path))
            with app.app_context():
                row = SqlAttempt.query.one()
                self.assertEqual(row.query_text, "SELECT 1")
                self.assertEqual(get_subject_stats(1)[0]["subject"], "SQL")
                get_practice_history(1)
                db.session.remove()
                db.engine.dispose()
