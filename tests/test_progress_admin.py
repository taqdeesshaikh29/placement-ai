"""Run with: python -m unittest discover -s tests -t ."""
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import (AptitudeAttempt, AttemptAnswer, InterviewQuestion, InterviewResponse, MockAnswer,
                        MockSession, PythonAttempt, Question, QuizResult, SqlAttempt, User)
from app.stats import (get_incorrect_answers, get_practice_history, get_quiz_trend, get_subject_stats)
from tests.test_mock_interview import Base

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


def add_quiz(uid, category, correct, total, token, days_ago=0, wrong_qids=()):
    """Save one quiz the way aptitude.submit does; `wrong_qids` become incorrect answers."""
    qs = Question.query.filter_by(category=category).limit(total).all()
    result = QuizResult(user_id=uid, subject=category, total_questions=total, correct_answers=correct,
                        created_at=NOW - timedelta(days=days_ago))
    attempt = AptitudeAttempt(token=token, user_id=uid, result=result, category=category,
                              difficulty="Mixed", time_taken=60)
    for i, q in enumerate(qs):
        bad = i >= correct
        attempt.answers.append(AttemptAnswer(question_id=q.id, is_correct=not bad,
                                             selected_option=(q.correct_option % 4) + 1 if bad else q.correct_option))
    db.session.add(attempt)
    db.session.commit()
    return attempt


class ProgressBase(Base):
    def setUp(self):
        super().setUp()
        with self.app.app_context():
            admin = User(name="Admin", email="a@example.com", role="admin")
            admin.set_password("password123")
            db.session.add(admin)
            db.session.commit()
            self.admin_id = admin.id


class ProgressCalculationTests(ProgressBase):
    def seed(self):
        a1 = add_quiz(self.uid, "Quantitative Aptitude", 3, 5, "t1", days_ago=3)
        add_quiz(self.uid, "Quantitative Aptitude", 5, 5, "t2", days_ago=1)
        add_quiz(self.uid, "Verbal Ability", 1, 4, "t3", days_ago=2)
        db.session.add_all([
            PythonAttempt(user_id=self.uid, question_id=1, answer_text="wrong", is_correct=False, created_at=NOW),
            PythonAttempt(user_id=self.uid, question_id=1, answer_text="right", is_correct=True, created_at=NOW),
            PythonAttempt(user_id=self.uid, question_id=2, answer_text="bad", is_correct=False, created_at=NOW),
            SqlAttempt(user_id=self.uid, question_id=1, query_text="SELECT 1", is_correct=False, created_at=NOW),
            # another student's records must never leak in
            PythonAttempt(user_id=self.other_id, question_id=3, answer_text="x", is_correct=True, created_at=NOW),
        ])
        db.session.commit()
        add_quiz(self.other_id, "Logical Reasoning", 5, 5, "other1")
        return a1.id

    def test_subject_accuracy(self):
        with self.app.app_context():
            self.seed()
            subjects = {s["subject"]: s for s in get_subject_stats(self.uid)}
        self.assertEqual(set(subjects), {"Quantitative Aptitude", "Verbal Ability", "Python", "SQL"})
        q = subjects["Quantitative Aptitude"]
        self.assertEqual((q["attempted"], q["correct"], q["accuracy"]), (10, 8, 80))
        self.assertEqual(subjects["Verbal Ability"]["accuracy"], 25)
        self.assertEqual((subjects["Python"]["attempted"], subjects["Python"]["correct"]), (3, 1))
        self.assertEqual(subjects["Python"]["accuracy"], 33)
        self.assertEqual(subjects["SQL"]["accuracy"], 0)

    def test_no_records_gives_empty_results(self):
        with self.app.app_context():
            self.assertEqual(get_subject_stats(self.uid), [])
            self.assertEqual(get_quiz_trend(self.uid), [])
            self.assertEqual(get_practice_history(self.uid), [])
            self.assertEqual(get_incorrect_answers(self.uid), [])
        html = self.client.get("/progress/").get_data(as_text=True)
        self.assertIn("No data yet", html)
        self.assertIn("No practice yet", html)

    def test_quiz_trend_is_chronological(self):
        with self.app.app_context():
            self.seed()
            trend = get_quiz_trend(self.uid)
        self.assertEqual([p["accuracy"] for p in trend], [60, 25, 100])  # 3 days ago, 2 days ago, yesterday

    def test_incorrect_answers(self):
        with self.app.app_context():
            self.seed()
            items = get_incorrect_answers(self.uid)
            kinds = [i["kind"] for i in items]
            self.assertEqual(kinds.count("aptitude"), 2 + 3)  # 2 wrong in quiz 1, 3 wrong in the verbal quiz
            self.assertEqual(kinds.count("python"), 2)
            self.assertEqual(kinds.count("sql"), 1)
            py = {i["qid"]: i for i in items if i["kind"] == "python"}
            self.assertTrue(py[1]["solved_since"])
            self.assertFalse(py[2]["solved_since"])
            only_sql = get_incorrect_answers(self.uid, "SQL")
            self.assertEqual({i["kind"] for i in only_sql}, {"sql"})
            only_verbal = get_incorrect_answers(self.uid, "Verbal Ability")
            self.assertEqual(len(only_verbal), 3)

    def test_history_merges_sources_newest_first(self):
        with self.app.app_context():
            self.seed()
            history = get_practice_history(self.uid)
        self.assertEqual(len(history), 3 + 3 + 1)
        self.assertEqual([h["when"] for h in history], sorted((h["when"] for h in history), reverse=True))
        self.assertTrue(all(h["endpoint"] for h in history))

    def test_pages_render_with_saved_data(self):
        with self.app.app_context():
            self.seed()
        html = self.client.get("/progress/").get_data(as_text=True)
        self.assertIn("subjectChart", html)
        self.assertIn("trendChart", html)
        self.assertIn("chart.js@4.4.3", html)
        self.assertIn("3/5 (60%)", html)
        review = self.client.get("/progress/review").get_data(as_text=True)
        self.assertIn("Your answer", review)
        self.assertIn("SELECT 1", review)
        filtered = self.client.get("/progress/review?subject=SQL").get_data(as_text=True)
        self.assertIn("SELECT 1", filtered)
        self.assertNotIn("Quantitative Aptitude</span>", filtered)
        junk = self.client.get("/progress/review?subject=%3Cscript%3E")
        self.assertEqual(junk.status_code, 200)
        self.assertNotIn("<script>alert", junk.get_data(as_text=True))

    def test_interview_history(self):
        with self.app.app_context():
            qid = InterviewQuestion.query.first().id
            db.session.add(InterviewResponse(user_id=self.uid, question_id=qid, response_text="mine",
                                             created_at=NOW, updated_at=NOW))
            ms = MockSession(user_id=self.uid, topic="Python", difficulty="Easy", mode="ai",
                             question_ids=str(qid), completed_at=NOW)
            ms.answers.append(MockAnswer(position=0, question_id=qid, answer_text="a", source="ai",
                                         feedback_json='{"scores": {"correctness": 8, "clarity": 6, "completeness": 4}}'))
            db.session.add(ms)
            db.session.commit()
        html = self.client.get("/progress/").get_data(as_text=True)
        self.assertIn("AI average 6.0/10", html)
        self.assertIn(f"/interview/question/{qid}", html)


class ProgressAuthorizationTests(ProgressBase):
    def test_anonymous_redirected(self):
        anon = self.app.test_client()
        for url in ("/progress/", "/progress/review"):
            self.assertEqual(anon.get(url).status_code, 302)

    def test_admin_cannot_use_student_progress(self):
        c = self.app.test_client()
        self.login("a@example.com", c)
        self.assertEqual(c.get("/progress/").status_code, 403)

    def test_students_only_see_their_own_records(self):
        with self.app.app_context():
            attempt_id = add_quiz(self.uid, "Quantitative Aptitude", 1, 3, "mine").id
            db.session.add(SqlAttempt(user_id=self.uid, question_id=1, query_text="SELECT secret_marker",
                                      is_correct=False, created_at=NOW))
            db.session.commit()
        other = self.app.test_client()
        self.login("o@example.com", other)
        for url in ("/progress/", "/progress/review"):
            html = other.get(url).get_data(as_text=True)
            self.assertNotIn("secret_marker", html)
            self.assertNotIn(f"/aptitude/result/{attempt_id}", html)
        self.assertEqual(other.get(f"/aptitude/result/{attempt_id}").status_code, 404)
        self.assertEqual(self.client.get(f"/aptitude/result/{attempt_id}").status_code, 200)

    def test_dashboard_matches_progress_numbers(self):
        with self.app.app_context():
            add_quiz(self.uid, "Quantitative Aptitude", 4, 5, "d1")
            db.session.add(SqlAttempt(user_id=self.uid, question_id=1, query_text="q", is_correct=True,
                                      created_at=NOW))
            db.session.commit()
        html = self.client.get("/dashboard").get_data(as_text=True)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        self.assertIn('data-subjects', html)
        self.assertIn("SQL", html)


class AdminAuthorizationTests(ProgressBase):
    URLS = ["/admin/", "/admin/aptitude", "/admin/interview", "/admin/aptitude/new", "/admin/interview/new",
            "/admin/aptitude/1/edit", "/admin/interview/1/edit"]

    def test_students_get_403_everywhere(self):
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        for url in ("/admin/aptitude/new", "/admin/aptitude/1/edit", "/admin/aptitude/1/delete",
                    "/admin/interview/1/delete"):
            self.assertEqual(self.client.post(url, data={"text": "x"}).status_code, 403, url)
        with self.app.app_context():
            self.assertIsNotNone(db.session.get(Question, 1))

    def test_anonymous_redirected_to_login(self):
        anon = self.app.test_client()
        for url in self.URLS:
            r = anon.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login", r.headers["Location"])
        self.assertEqual(anon.post("/admin/aptitude/1/delete").status_code, 302)

    def test_admin_allowed_and_logs_in_to_admin_home(self):
        c = self.app.test_client()
        r = c.post("/login", data={"email": "a@example.com", "password": "password123"})
        self.assertTrue(r.headers["Location"].endswith("/admin/"))
        for url in self.URLS:
            self.assertEqual(c.get(url).status_code, 200, url)

    def test_cannot_register_as_admin(self):
        c = self.app.test_client()
        c.post("/register", data={"name": "Eve", "email": "eve@example.com", "password": "password123",
                                  "confirm_password": "password123", "role": "admin"})
        with self.app.app_context():
            self.assertEqual(User.query.filter_by(email="eve@example.com").one().role, "student")

    def test_promote_command(self):
        runner = self.app.test_cli_runner()
        ok = runner.invoke(args=["admin", "promote", "O@example.com"])
        self.assertEqual(ok.exit_code, 0, ok.output)
        with self.app.app_context():
            self.assertEqual(db.session.get(User, self.other_id).role, "admin")
        bad = runner.invoke(args=["admin", "promote", "nobody@example.com"])
        self.assertNotEqual(bad.exit_code, 0)

    def test_unknown_kind_is_404(self):
        c = self.app.test_client()
        self.login("a@example.com", c)
        self.assertEqual(c.get("/admin/users").status_code, 404)


class AdminCsrfTests(ProgressBase):
    config_overrides = {"WTF_CSRF_ENABLED": True}

    def test_post_without_csrf_token_is_rejected(self):
        c = self.app.test_client()
        with c.session_transaction() as s:
            s["_user_id"], s["_fresh"] = str(self.admin_id), True
        before = self.count(Question)
        self.assertEqual(c.post("/admin/aptitude/1/delete").status_code, 400)
        self.assertEqual(self.count(Question), before)

    def count(self, model):
        with self.app.app_context():
            return model.query.count()


APT = {"category": "Verbal Ability", "difficulty": "Easy", "text": "Pick the synonym of 'big'.",
       "option_1": "Large", "option_2": "Tiny", "option_3": "Dull", "option_4": "Slow",
       "correct_option": "1", "explanation": "Large means big."}
INT = {"kind": "technical", "category": "Python", "difficulty": "Easy", "text": "What is a decorator?",
       "key_concepts": "Functions as objects\nWrapping behaviour", "sample_answer": "A function that wraps another."}


class AdminQuestionTests(ProgressBase):
    def setUp(self):
        super().setUp()
        self.adm = self.app.test_client()
        self.login("a@example.com", self.adm)

    def test_create_edit_delete_aptitude(self):
        with self.app.app_context():
            before = Question.query.count()
        r = self.adm.post("/admin/aptitude/new", data=APT)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            self.assertEqual(Question.query.count(), before + 1)
            q = Question.query.order_by(Question.id.desc()).first()
            self.assertEqual((q.option_1, q.correct_option), ("Large", 1))
            qid = q.id
        self.adm.post(f"/admin/aptitude/{qid}/edit", data=dict(APT, text="Pick a synonym of 'huge'.", correct_option="2"))
        with self.app.app_context():
            q = db.session.get(Question, qid)
            self.assertEqual((q.text, q.correct_option), ("Pick a synonym of 'huge'.", 2))
        self.adm.post(f"/admin/aptitude/{qid}/delete")
        with self.app.app_context():
            self.assertIsNone(db.session.get(Question, qid))

    def test_aptitude_validation(self):
        with self.app.app_context():
            before = Question.query.count()
        for bad in (dict(APT, text=""), dict(APT, category="Nope"), dict(APT, correct_option="9"),
                    dict(APT, option_2=""), dict(APT, option_1="x" * 300)):
            self.assertEqual(self.adm.post("/admin/aptitude/new", data=bad).status_code, 200)
        with self.app.app_context():
            self.assertEqual(Question.query.count(), before)

    def test_answered_question_keeps_answer_key_and_cannot_be_deleted(self):
        with self.app.app_context():
            attempt = add_quiz(self.uid, "Quantitative Aptitude", 1, 2, "locked")
            qid = attempt.answers[0].question_id
            original = db.session.get(Question, qid)
            data = {"category": original.category, "difficulty": original.difficulty, "text": original.text,
                    "option_1": original.option_1, "option_2": original.option_2, "option_3": original.option_3,
                    "option_4": original.option_4, "correct_option": str(original.correct_option),
                    "explanation": original.explanation}
            old_correct = original.correct_option
        changed = dict(data, correct_option=str(old_correct % 4 + 1))
        r = self.adm.post(f"/admin/aptitude/{qid}/edit", data=changed)
        self.assertEqual(r.status_code, 200)
        self.assertIn("cannot change", r.get_data(as_text=True))
        r = self.adm.post(f"/admin/aptitude/{qid}/edit", data=dict(data, explanation="Better explanation."))
        self.assertEqual(r.status_code, 302)
        self.adm.post(f"/admin/aptitude/{qid}/delete")
        with self.app.app_context():
            q = db.session.get(Question, qid)
            self.assertIsNotNone(q)
            self.assertEqual((q.correct_option, q.explanation), (old_correct, "Better explanation."))
        # the student's saved history still renders
        self.assertEqual(self.client.get("/progress/review").status_code, 200)

    def test_create_edit_delete_interview(self):
        r = self.adm.post("/admin/interview/new", data=INT)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            q = InterviewQuestion.query.order_by(InterviewQuestion.id.desc()).first()
            self.assertEqual(q.key_concepts, "Functions as objects|Wrapping behaviour")
            qid = q.id
        page = self.adm.get(f"/admin/interview/{qid}/edit").get_data(as_text=True)
        self.assertIn("Functions as objects\nWrapping behaviour", page)
        self.adm.post(f"/admin/interview/{qid}/edit", data=dict(INT, key_concepts="One concept"))
        with self.app.app_context():
            self.assertEqual(db.session.get(InterviewQuestion, qid).concepts, ["One concept"])
        self.adm.post(f"/admin/interview/{qid}/delete")
        with self.app.app_context():
            self.assertIsNone(db.session.get(InterviewQuestion, qid))

    def test_interview_validation(self):
        with self.app.app_context():
            before = InterviewQuestion.query.count()
        for bad in (dict(INT, category="Teamwork"),  # HR category on a technical question
                    dict(INT, key_concepts="a|b"), dict(INT, key_concepts="  \n "), dict(INT, kind="other")):
            self.assertEqual(self.adm.post("/admin/interview/new", data=bad).status_code, 200)
        with self.app.app_context():
            self.assertEqual(InterviewQuestion.query.count(), before)

    def test_interview_question_in_use_cannot_be_deleted(self):
        with self.app.app_context():
            q = InterviewQuestion.query.first()
            qid = q.id
            db.session.add(InterviewResponse(user_id=self.uid, question_id=qid, response_text="mine",
                                             created_at=NOW, updated_at=NOW))
            db.session.commit()
        self.adm.post(f"/admin/interview/{qid}/delete")
        with self.app.app_context():
            self.assertIsNotNone(db.session.get(InterviewQuestion, qid))

    def test_question_in_unfinished_mock_session_cannot_be_deleted(self):
        with self.app.app_context():
            qid = InterviewQuestion.query.first().id
            db.session.add(MockSession(user_id=self.uid, topic="Python", difficulty="Easy", mode="fallback",
                                       question_ids=f"{qid}"))
            db.session.commit()
        self.adm.post(f"/admin/interview/{qid}/delete")
        with self.app.app_context():
            self.assertIsNotNone(db.session.get(InterviewQuestion, qid))

    def test_list_pagination_and_filter(self):
        html = self.adm.get("/admin/aptitude?category=Verbal+Ability").get_data(as_text=True)
        self.assertIn("Verbal Ability", html)
        self.assertNotIn("Quantitative Aptitude</span>", html)
        self.assertEqual(self.adm.get("/admin/aptitude?page=999").status_code, 200)
