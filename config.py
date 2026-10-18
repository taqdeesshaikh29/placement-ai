import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_env_file(path):
    """Load KEY=VALUE lines from .env into os.environ (real environment variables win)."""
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(os.path.join(BASE_DIR, ".env"))


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    APP_NAME = "PlacementAI"

    # SQLite file lives in instance/
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "placement.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Separate database used only by the SQL Lab (never the application database)
    SQL_PRACTICE_DB = os.path.join(BASE_DIR, "instance", "sql_practice.db")

    # AI Mock Interview. Leave LLM_API_KEY unset to run in labelled fallback mode.
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()  # "anthropic" or "openai" (OpenAI-compatible)
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_MODEL = os.environ.get("LLM_MODEL", "")  # empty = provider default
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")  # empty = provider default
    LLM_TIMEOUT = _int_env("LLM_TIMEOUT", 20)  # seconds
    LLM_MAX_OUTPUT_TOKENS = _int_env("LLM_MAX_OUTPUT_TOKENS", 600)
    LLM_DAILY_LIMIT_PER_USER = _int_env("LLM_DAILY_LIMIT_PER_USER", 30)  # AI calls per 24h

    # Sessions / cookies
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # requires HTTPS
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True

    def __init__(self):
        if Config.SECRET_KEY == "dev-change-me":
            raise RuntimeError("Set SECRET_KEY in the environment (or .env) before running in production.")
