# AI Career interest test (MVP)

Python backend reads questionnaire answers from **Google Sheets** (fed by **Tally**), calls an **LLM** to score a configurable job list, stores structured results, and serves a simple **HTML/JS** results page.

## Data flow

1. User completes the Tally form; Tally appends **one row per respondent** to the **Responses** sheet (include an **email** column and one column per question, e.g. `Q1`, `Q2`, `Q3`).
2. The backend **POST `/api/process`** reads unprocessed rows, calls the LLM, writes the **Results** sheet, and sets **`processed`** to `TRUE` on the response row.
3. **GET `/api/results?email=...`** reads the saved result for that email.
4. **`/results.html?email=...`** loads scores, top jobs, and summary via the API (it will trigger processing once if results are missing, then poll).

## Run locally

```bash
cd Career
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`: set **`OPENAI_API_KEY`** or **`GEMINI_API_KEY`**, **`SPREADSHEET_ID`**, and **`GOOGLE_SERVICE_ACCOUNT_FILE`**.

Start the API:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000/results.html?email=demo@example.com](http://localhost:8000/results.html?email=demo@example.com).

### Demo without Google Sheets

Set **`USE_MOCK_SHEETS=true`** in `.env`. A sample row for `demo@example.com` is used; you still need a valid LLM API key.

## Google Sheets setup

1. Create a Google Cloud project, enable **Google Sheets API**, create a **service account**, download the JSON key.
2. Share your spreadsheet with the service account email (Editor).
3. **Responses** tab: first row headers must include **`email`**, your question columns (default **`Q1`**, **`Q2`**, **`Q3`**), and **`processed`** (can start empty).
4. **Results** tab: created automatically with columns **`email`**, **`top_jobs`** (JSON array), **`scores_json`** (JSON object), **`summary`**.

Environment variables for column or sheet names are in **`backend/config.py`** (see **`.env.example`**).

## Where to edit things

| What | Where |
|------|--------|
| LLM system prompt and user instructions | **`backend/prompt_templates.py`** |
| Default job list | **`backend/config.py`** → `default_jobs()`, or set **`JOBS_FILE`** to a JSON file like **`data/jobs.json`** |
| Models / API shapes | **`backend/models.py`** |
| OpenAI vs Gemini, models, sheet names | **`.env`** + **`backend/config.py`** |
| Sheet read/write | **`backend/sheets_client.py`** |
| Orchestration (answers → LLM → save) | **`backend/scoring_engine.py`** |
| Results UI | **`frontend/results.html`** |

## API

- **`GET /health`** — liveness check.
- **`GET /api/results?email=`** — JSON results for that email (404 if not stored yet).
- **`POST /api/process`** — body optional `{"email": "x@y.com"}` to process only that respondent, or `{}` to process **all** rows where `processed` is not true.

## Tally redirect

In Tally, set the thank-you screen redirect URL to your deployed site, e.g. `https://your-domain.com/results.html?email={field:email}` (use the correct merge tag for your email field).

## Deployment notes

Run **`uvicorn backend.main:app --host 0.0.0.0 --port 8000`** behind HTTPS (reverse proxy). Ensure environment variables are set on the host; do not commit secrets or service account JSON.
