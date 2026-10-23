# AgentForge

AgentForge is a local, authenticated AI document workspace. After signing in, describe a document and AgentForge plans, writes, reviews, validates, traces, and exports it as a Word document (`.docx`) using a local Ollama model.

## Highlights

- Local user accounts backed by SQLite and password hashing with PBKDF2.
- 24-hour HS256 JWT sessions for the browser and API.
- A typed multi-agent workflow: orchestrator -> planner -> writer -> reviewer -> DOCX generator.
- Bounded retries, model timeouts, validated outputs, and explicit failed-run states.
- Persistent SQLite tracing for every run: agents, models, attempts, token counts, handoffs, errors, and final outcome.
- Local Ollama inference; the default model is `qwen2.5:7b`.

For detailed agent boundaries, tool permissions, handoffs, and safety policy, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally
- The configured model:

```powershell
ollama pull qwen2.5:7b
```

## Setup

From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create a local JWT configuration file before deployment:

```powershell
Copy-Item .env.example .env
```

Set `JWT_SECRET` in `.env` to a long, random value. The default is only suitable for local development.

Verify the Ollama connection:

```powershell
python test_ollama.py
```

## Run

```powershell
.\.venv\Scripts\python.exe run.py
```

The development entry point deliberately runs without Uvicorn auto-reload to avoid the Windows named-pipe permission issue. Open [http://127.0.0.1:8000](http://127.0.0.1:8000), create an account, then sign in to access the document workspace.

## Workflow

```text
User request
  -> Orchestrator creates typed run state
  -> Planner returns a validated execution plan
  -> Writer produces one validated section per task
  -> Reviewer validates polished sections
  -> DOCX generator saves the final document
  -> Run trace is persisted in SQLite
```

The orchestrator is the only component that owns workflow state or writes a file. Specialist agents cannot call each other and have no tool permissions.

## API

All document and tracing endpoints require an `Authorization: Bearer <token>` header. Obtain a token from sign-up or login.

### Sign up

`POST /auth/signup`

```json
{
  "email": "you@example.com",
  "password": "at-least-8-characters"
}
```

### Log in

`POST /auth/login`

```json
{
  "email": "you@example.com",
  "password": "at-least-8-characters"
}
```

Both endpoints return an `access_token`, `token_type`, and public user object. Check the active user with `GET /auth/me`.

### Generate a document

`POST /agent`

```json
{
  "request": "Create a project proposal for a mobile fitness app."
}
```

Successful responses include `run_id`, the validated execution plan, reviewed section content, and the generated document path. Failed runs return HTTP `502` with a `run_id`; use it to inspect the trace.

### Inspect a run

`GET /runs/{run_id}`

Returns the status and ordered trace events for the authenticated owner. Events show the agent, model, attempt, token counts supplied by Ollama, tool list, timestamps, and error details when applicable.

### Download a document

`GET /documents/{filename}`

Documents are saved locally in `output/` and must be downloaded with the same Bearer token.

## Project structure

```text
app/
  agents/                    Planner, writer, reviewer, retry policy
  api/                       Authentication, document, and trace routes
  core/                      JWT/authentication and SQLite tracing
  document/                  Safe DOCX generation
  executor/                  Orchestrator and workflow handoffs
  llm/                       Ollama client with timeouts and metadata
  models/                    API schemas and typed workflow contracts
  static/                    Login and document-workspace frontend
  utils/                     LLM prompts and utilities
tests/                       Isolated workflow verification
ARCHITECTURE.md              Agent contracts and operational safeguards
pyproject.toml               Project and pytest configuration
requirements.txt             Pinned runtime and development dependencies
```

## Validation and troubleshooting

Run the test suite after installing dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

- **Page does not load:** Run `python run.py` from the activated virtual environment; `run.py` uses `reload=False` for Windows compatibility.
- **Ollama connection failed:** Start Ollama and confirm its API is at `http://localhost:11434`.
- **Model not found:** Run `ollama pull qwen2.5:7b`, or set another local model in `app/llm/ollama_client.py`.
- **A document run failed:** Retrieve `GET /runs/{run_id}` while signed in; the trace contains the failing agent, retry attempt, and error.
