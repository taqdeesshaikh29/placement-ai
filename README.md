# PlacementAI – Placement Preparation System

A Flask web app where students practise for campus placements: aptitude quizzes, SQL and Python practice,
interview preparation, an AI mock interview (with a labelled fallback mode) and progress tracking.
Admins manage the aptitude and interview question banks.

## Features
- **Accounts:** register, log in, log out. Students and admins (admin is never self-service). Failed logins are throttled.
- **Aptitude:** timed 5-question quizzes (quantitative, logical, verbal), saved results and a full answer review.
- **SQL Lab:** write SELECT queries against a separate, read-only practice database; answers are checked automatically.
- **Python Practice:** predefined questions (predict the output, fill the blank, multiple choice). No student code is ever executed.
- **Interview preparation:** technical and HR questions with key concepts, sample answers and your own saved answers.
- **AI Mock Interview:** choose a topic and difficulty, answer one question at a time, get feedback on correctness, clarity and
  completeness, a sample answer and an optional follow-up. Works without an AI key in a clearly labelled fallback mode.
- **Progress:** accuracy by subject, quiz scores over time (Chart.js), practice history, incorrect answers to review, interview history.
- **Admin:** create, edit and delete aptitude and interview questions.

## Setup on Windows (PowerShell)
Requires Python 3.11 or newer.
```powershell
cd "C:\Users\Dell\Desktop\AI Placement"
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

## Configuration
Settings come from environment variables, or from a `.env` file in the project folder (copied from `.env.example`).
Real environment variables take priority over `.env`. `.env` is git-ignored: never commit keys.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs sessions. Required when `APP_ENV=production`. |
| `APP_ENV` | `development` (default) or `production` (no debug, HTTPS-only cookies). |
| `LLM_API_KEY` | AI key for the mock interview. Empty = fallback mode, no AI calls. |
| `LLM_PROVIDER` | `anthropic` (default) or `openai` (any OpenAI-compatible API). |
| `LLM_MODEL`, `LLM_BASE_URL` | Optional overrides; empty uses the provider defaults. |
| `LLM_TIMEOUT`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_DAILY_LIMIT_PER_USER` | Cost and safety limits (20 s, 600 tokens, 30 AI calls per student per 24 h). |

Fallback mode shows predefined sample answers and a simple keyword check. It never produces scores and is always labelled
"NOT AI-generated". It is also used for any answer where the AI call fails or the daily limit is reached.

## Database
SQLite files live in `instance/`. There is nothing to initialise by hand: on startup the app creates any missing tables,
loads the sample aptitude and interview questions into empty tables, and creates the SQL Lab practice database.
To start fresh, stop the app and delete `instance\placement.db` (and `instance\sql_practice.db`). There is no migration tool,
so changes to existing tables need a manual change or a reset.

## Run
```powershell
venv\Scripts\Activate.ps1
python run.py
```
Open http://127.0.0.1:5000

### Creating an admin
Register a normal account in the browser, then promote it:
```powershell
flask --app run admin promote you@example.com
```
Admins log in to `/admin/` (Manage questions). Admins do not have the student pages.

## Tests
```powershell
venv\Scripts\python.exe -m unittest discover -s tests -t .
```
The tests use temporary databases and mock the AI HTTP call, so no real API requests are made and your data is untouched.
They take a couple of minutes (password hashing dominates).

## Structure
- `run.py`, `config.py` – entry point and settings
- `app/` – blueprints (`auth`, `aptitude`, `sql_lab`, `python_lab`, `interview`, `progress`, `admin`), `models.py`, `stats.py`, `llm.py`
- `app/templates/`, `app/static/` – Jinja templates, CSS and JavaScript
- `tests/` – unit and integration tests

## Limitations
- Question banks are small (the interview bank has two questions per topic, so mock interviews are short).
- Python and SQL Lab questions are defined in code and cannot be edited from the admin screen.
- Mock interview questions are taken from the bank; the AI only assesses answers.
- The login throttle is in memory: it resets on restart and is per process.
- No email verification or password reset. No schema migrations.
- Chart.js, Bootstrap and fonts load from CDNs, so the pages need internet access.
- Built for a single server using SQLite, not for heavy concurrent use.
