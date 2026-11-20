# AI Chat Application — Week 5 Day 5

A starter project for the frontend, streaming, session history, authentication,
rate limiting, tests, README and demo requirements in the supplied assignment.

## Requirements
- Python 3.10+
- VS Code (optional)
- A modern browser

## Setup (Windows PowerShell)

```powershell
cd "D:\Training\integrated AI\ai_chat_application"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and change `APP_API_KEY` to a private value.

## Run

Terminal 1 — backend:

```powershell
uvicorn app.main:app --reload
```

Terminal 2 — frontend:

```powershell
cd frontend
py -m http.server 5500
```

Open http://127.0.0.1:5500 and enter the same `APP_API_KEY` value from `.env`
in the App API key settings field.

## API list

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/sessions` | List sessions |
| POST | `/api/sessions` | Create a session |
| GET | `/api/sessions/{id}/messages` | Load chat history |
| POST | `/api/sessions/{id}/stream` | Stream a reply as Server-Sent Events |
| GET | `/api/usage` | Basic usage report |

All `/api` endpoints require the `X-API-Key` header. The demo key is
`local-demo-key` unless changed in `.env`.

## Tests

```powershell
pytest -q
```

Optional coverage report:

```powershell
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

The tests cover authentication, session history/isolation, streaming, rate
limiting and usage. Coverage percentage can vary by environment; run the
coverage command to verify it.

## Architecture

- `frontend/`: HTML, CSS and JavaScript UI; progressive SSE rendering.
- `app/main.py`: FastAPI API, demo stream, authentication, rate limiting and
  in-memory session storage.
- `tests/`: API tests using FastAPI TestClient.

## Important limitations before production

This is a runnable learning starter. It uses in-memory sessions, so data is
lost when the server restarts and it is not suitable for multiple workers.
The streamed answer is a mock response, not a real LLM completion. Replace
`demo_reply()` in `app/main.py` with your provider's streaming SDK and keep
provider credentials on the server in environment variables. The browser
settings field here is for the app API key; do not put a permanent provider
secret in frontend code or browser storage. Configure `CORS_ORIGINS` narrowly.

## Five-minute demo checklist

1. Create a new session.
2. Send a message and show the progressive streamed reply.
3. Open another session and reload the earlier history.
4. Demonstrate a rate-limit response (temporarily set `RATE_LIMIT=1`).
5. Show `/api/usage`.
6. Explain: if the LLM is down, return a clear error/fallback and log the failure;
   control cost with rate limits, token limits, model selection and usage tracking.
7. Bonus: click **Stop generating** while a response is streaming.
