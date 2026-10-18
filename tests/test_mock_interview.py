"""Run with: python -m unittest discover -s tests"""
import json
import os
import re
import tempfile
import unittest
from unittest import mock

from app import create_app, llm
from app.extensions import db
from app.models import MockAnswer, MockSession, User
from config import Config

AI_REPLY = {
    "correctness": {"score": 8, "comment": "Mostly right."},
    "clarity": {"score": 7, "comment": "Clear."},
    "completeness": {"score": 6, "comment": "Missing an example."},
    "improvements": ["Add an example."],
    "sample_answer": "AI sample answer.",
    "follow_up": "When would you not use it?",
}


def make_config(tmp, **overrides):
    attrs = {"SQLALCHEMY_DATABASE_URI": "sqlite:///" + os.path.join(tmp, "t.db"),
             "SQL_PRACTICE_DB": os.path.join(tmp, "sql.db"), "WTF_CSRF_ENABLED": False, "TESTING": True,
             "LLM_API_KEY": "", "LLM_PROVIDER": "anthropic", "LLM_MODEL": "", "LLM_BASE_URL": "",
             "LLM_TIMEOUT": 5, "LLM_MAX_OUTPUT_TOKENS": 600, "LLM_DAILY_LIMIT_PER_USER": 30}
    attrs.update(overrides)
    return type("TestConfig", (Config,), attrs)


class Base(unittest.TestCase):
    config_overrides = {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(make_config(self.tmp.name, **self.config_overrides))
        self.client = self.app.test_client()
        with self.app.app_context():
            u = User(name="Stu", email="s@example.com", role="student")
            u.set_password("password123")
            other = User(name="Other", email="o@example.com", role="student")
            other.set_password("password123")
            db.session.add_all([u, other])
            db.session.commit()
            self.uid, self.other_id = u.id, other.id
        self.login("s@example.com")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tmp.cleanup()

    def login(self, email, client=None):
        (client or self.client).post("/login", data={"email": email, "password": "password123"})

    def start(self, topic="Python", difficulty="Easy", count="3", client=None):
        return (client or self.client).post("/interview/mock/start", data={
            "topic": topic, "difficulty": difficulty, "count": count})

    def answer(self, sid, text="A list is mutable and a tuple is immutable, hashable keys.", client=None):
        return (client or self.client).post(f"/interview/mock/{sid}/answer", data={"response": text})


class FallbackTests(Base):
    def test_page_is_labelled_fallback(self):
        html = self.client.get("/interview/mock").get_data(as_text=True)
        self.assertIn("Fallback mode", html)

    def test_full_flow_never_calls_api_and_is_labelled(self):
        with mock.patch.object(llm, "_post_json") as post:
            r = self.start()
            self.assertEqual(r.status_code, 302)
            sid = int(re.search(r"/mock/(\d+)", r.headers["Location"]).group(1))
            with self.app.app_context():
                n = len(db.session.get(MockSession, sid).ids)
            for i in range(n):
                self.assertEqual(self.answer(sid).status_code, 302)
                html = self.client.get(f"/interview/mock/{sid}/feedback/{i}").get_data(as_text=True)
                self.assertIn("NOT AI-generated", html)
                self.assertNotIn("AI-generated feedback<", html)
                self.assertIn("Sample answer", html)
            post.assert_not_called()
        summary = self.client.get(f"/interview/mock/{sid}/summary").get_data(as_text=True)
        self.assertIn("not AI", summary)
        with self.app.app_context():
            ms = db.session.get(MockSession, sid)
            self.assertEqual(ms.mode, "fallback")
            self.assertIsNotNone(ms.completed_at)
            self.assertTrue(all(a.source == "fallback" and a.fallback_reason == "no_key" for a in ms.answers))
            self.assertIsNone(json.loads(ms.answers[0].feedback_json)["scores"])

    def test_validation(self):
        for bad in [dict(topic="Nope"), dict(difficulty="Insane"), dict(count="99"), dict(count="x")]:
            r = self.start(**bad)
            self.assertTrue(r.headers["Location"].endswith("/interview/mock"))
        with self.app.app_context():
            self.assertEqual(MockSession.query.count(), 0)
        sid = int(re.search(r"/mock/(\d+)", self.start().headers["Location"]).group(1))
        self.assertEqual(self.answer(sid, "   ").status_code, 400)
        self.assertEqual(self.answer(sid, "x" * 1501).status_code, 400)
        with self.app.app_context():
            self.assertEqual(MockAnswer.query.count(), 0)

    def test_other_students_session_is_404(self):
        sid = int(re.search(r"/mock/(\d+)", self.start().headers["Location"]).group(1))
        other = self.app.test_client()
        self.login("o@example.com", other)
        self.assertEqual(other.get(f"/interview/mock/{sid}").status_code, 404)
        self.assertEqual(self.answer(sid, client=other).status_code, 404)

    def test_difficulty_is_a_preference(self):
        # Python has Easy + Medium only; asking for Hard still yields a (nearest-first) session
        sid = int(re.search(r"/mock/(\d+)", self.start(difficulty="Hard", count="5").headers["Location"]).group(1))
        with self.app.app_context():
            ms = db.session.get(MockSession, sid)
            self.assertEqual(len(ms.ids), 2)
            from app.models import InterviewQuestion
            self.assertEqual(db.session.get(InterviewQuestion, ms.ids[0]).difficulty, "Medium")

    def test_login_required(self):
        anon = self.app.test_client()
        self.assertEqual(anon.get("/interview/mock").status_code, 302)

    def test_active_session_cap(self):
        for _ in range(3):
            self.start()
        r = self.start()
        self.assertTrue(r.headers["Location"].endswith("/interview/mock"))

    def test_keyword_check(self):
        with self.app.app_context():
            from app.models import InterviewQuestion
            q = InterviewQuestion.query.filter_by(category="Python", difficulty="Easy").first()
            fb = llm.fallback_feedback(q, "Lists are mutable but tuples are immutable.")
            self.assertIn("Mutability", fb["covered"])
            self.assertIsNone(fb["scores"])


class ConfiguredTests(Base):
    config_overrides = {"LLM_API_KEY": "test-key"}

    def _sid(self):
        return int(re.search(r"/mock/(\d+)", self.start().headers["Location"]).group(1))

    def test_ai_feedback_saved_and_labelled(self):
        reply = {"content": [{"type": "text", "text": "Sure:\n" + json.dumps(AI_REPLY)}]}
        with mock.patch.object(llm, "_post_json", return_value=reply) as post:
            sid = self._sid()
            self.assertEqual(self.answer(sid).status_code, 302)
        args = post.call_args.args
        self.assertEqual(args[0], "https://api.anthropic.com/v1/messages")
        self.assertEqual(args[1]["x-api-key"], "test-key")
        self.assertEqual(args[2]["max_tokens"], 600)
        self.assertIn("<answer>", args[2]["messages"][0]["content"])
        html = self.client.get(f"/interview/mock/{sid}/feedback/0").get_data(as_text=True)
        self.assertIn("AI-generated feedback", html)
        self.assertIn("AI sample answer.", html)
        self.assertIn("When would you not use it?", html)
        self.assertNotIn("NOT AI-generated", html)
        with self.app.app_context():
            a = MockAnswer.query.one()
            self.assertEqual(a.source, "ai")

    def test_openai_provider_shape(self):
        self.app.config.update(LLM_PROVIDER="openai", LLM_BASE_URL="https://llm.example/v1/chat/completions")
        reply = {"choices": [{"message": {"content": json.dumps(AI_REPLY)}}]}
        with mock.patch.object(llm, "_post_json", return_value=reply) as post:
            sid = self._sid()
            self.answer(sid)
        self.assertEqual(post.call_args.args[0], "https://llm.example/v1/chat/completions")
        self.assertEqual(post.call_args.args[1]["authorization"], "Bearer test-key")
        with self.app.app_context():
            self.assertEqual(MockAnswer.query.one().source, "ai")

    def test_api_failure_falls_back_with_label(self):
        with mock.patch.object(llm, "_post_json", side_effect=llm.LLMError("The AI service could not be reached or timed out.")):
            sid = self._sid()
            self.assertEqual(self.answer(sid).status_code, 302)
        html = self.client.get(f"/interview/mock/{sid}/feedback/0").get_data(as_text=True)
        self.assertIn("NOT AI-generated", html)
        self.assertIn("could not be reached", html)
        self.assertNotIn("test-key", html)

    def test_malformed_reply_falls_back(self):
        with mock.patch.object(llm, "_post_json", return_value={"content": [{"type": "text", "text": "not json"}]}):
            sid = self._sid()
            self.answer(sid)
        with self.app.app_context():
            self.assertEqual(MockAnswer.query.one().source, "fallback")

    def test_scores_are_clamped(self):
        bad = dict(AI_REPLY, correctness={"score": 99, "comment": "x"})
        self.assertEqual(llm._parse(json.dumps(bad))["scores"]["correctness"], 10)

    def test_daily_limit_switches_to_fallback(self):
        self.app.config["LLM_DAILY_LIMIT_PER_USER"] = 1
        reply = {"content": [{"type": "text", "text": json.dumps(AI_REPLY)}]}
        with mock.patch.object(llm, "_post_json", return_value=reply) as post:
            sid = self._sid()
            self.answer(sid)
            self.answer(sid)
            self.assertEqual(post.call_count, 1)
        html = self.client.get(f"/interview/mock/{sid}/feedback/1").get_data(as_text=True)
        self.assertIn("daily AI feedback limit", html)
        self.assertIn("NOT AI-generated", html)

    def test_summary_averages_only_ai_answers(self):
        reply = {"content": [{"type": "text", "text": json.dumps(AI_REPLY)}]}
        with mock.patch.object(llm, "_post_json", return_value=reply):
            sid = self._sid()
            self.answer(sid)
        with mock.patch.object(llm, "_post_json", side_effect=llm.LLMError("down")):
            self.answer(sid)
        html = self.client.get(f"/interview/mock/{sid}/summary").get_data(as_text=True)
        self.assertIn("1 AI-assessed answer", html)

    def test_api_key_never_rendered(self):
        sid = self._sid()
        for url in ["/interview/mock", f"/interview/mock/{sid}"]:
            self.assertNotIn("test-key", self.client.get(url).get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
