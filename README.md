# AI career interest test

Python **FastAPI** service reads questionnaire answers from **Google Sheets** (usually via **Tally**), ranks jobs in **Python**, asks **Gemini** or **OpenAI** for short explanations, stores results in Sheets, and serves a small **HTML/JS** results page.

Prompt and scoring rules follow [docs/MANUAL_CHATGPT_PROMPT_TEMPLATE.md](docs/MANUAL_CHATGPT_PROMPT_TEMPLATE.md). Delivery notes and architecture are in [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md).

## How it works

1. A respondent completes the Tally form; Tally appends one row to the configured **Responses** tab (`email`, **A1–F8**; **`processed`** is optional).
2. **`GET /api/results?email=&job_set=`** reads that row from Sheets, validates answers, ranks jobs in Python, calls the LLM for French explanations only, returns JSON, and may write a copy to the **Results** tab.
3. **`/results.html?email=...`** loads the results page and calls the API (same origin when you use Uvicorn as below).

Ranking is deterministic in code. The LLM does not change job order or scores.

## Run on localhost

Do everything from the **repository root** (`ai-interest-career/`). Do not use `python -m http.server` alone — it cannot serve `/api/*`.

### 1. One-time setup

```powershell
cd D:\Task\Upwork\Belgium\ai-interest-career
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
copy .env.example .env
```

On **cmd.exe**: `\.venv\Scripts\activate.bat`

### 2. Configure `.env`

Minimum for a quick test (no Google):

```env
GEMINI_API_KEY=your_key_here
USE_MOCK_SHEETS=true
```

For **live Google Sheets**, also set `SPREADSHEET_ID`, `RESPONSES_SHEET_NAME`, `RESULTS_SHEET_NAME`, and service account fields (see below). Set `USE_MOCK_SHEETS=false`.

Restart the server after any `.env` change.

### 3. Start the server

```powershell
python -m uvicorn main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

Keep this terminal open. You should see `Uvicorn running on http://0.0.0.0:8000`.

### 4. Open in the browser

| URL | Purpose |
|-----|---------|
| http://localhost:8000/health | API alive (`{"status":"ok"}`) |
| http://localhost:8000/results.html?email=demo@example.com | Mock demo (needs `USE_MOCK_SHEETS=true`) |
| http://localhost:8000/results.html?email=you@example.com&job_set=core_30 | Live row from Sheets |
| http://localhost:8000/results.html?email=you@example.com&job_set=client_40 | Extended job catalog |

The page and API must share the same host (`localhost:8000`) so the browser can call `/api/results`.

### Demo without Google Sheets

Set **`USE_MOCK_SHEETS=true`** in `.env`. Mock mode serves one sample **A1–F8** row for **`demo@example.com`** only. You still need a valid **`GEMINI_API_KEY`** (or OpenAI).

### Live Google Sheets on localhost

### Live Google Sheets

1. Create a service account in Google Cloud, enable the **Google Sheets API**, and download the JSON key.
2. Save the key at `secrets/service-account.json` (or another path and set **`GOOGLE_SERVICE_ACCOUNT_FILE`**). Paths in `.env` resolve from the repository root.
3. Share the target spreadsheet with the service account **`client_email`** as **Editor**.
4. Set **`SPREADSHEET_ID`** to that spreadsheet’s ID.
5. Set **`RESPONSES_SHEET_NAME`** and **`RESULTS_SHEET_NAME`** to the **exact** tab names in the file. Tally or an import may use a name other than `Responses` (for example a CSV filename).
6. On the **Responses** tab, row 1 must include **`email`** and **`A1` … `F8`** (`processed` optional). On **Results**, create row 1 with **`email`**, **`user_dimension_vector`**, **`top_jobs`**, and **`summary`** if the tab does not exist yet.
7. Open the results page with an **email** that exists on the Responses tab, for example `http://localhost:8000/results.html?email=demo1@example.com`.

If a tab name in `.env` does not match the spreadsheet, the API error lists the tab names that were found.

### Quick checks

```powershell
python scripts\try_llm.py data\test_answers.json
python scripts\try_llm.py --scores-only data\benchmark_samples.json
python scripts\run_benchmark.py
python -m pytest tests
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `gemini` (default) or `openai` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | LLM credentials |
| `GEMINI_MODEL` / `OPENAI_MODEL` | Model name (`gemini-2.5-flash` by default) |
| `LLM_TEMPERATURE` | Explanation temperature (default `0.3`) |
| `GOOGLE_SERVICE_ACCOUNT_*` | Service account fields in `.env`, or `GOOGLE_SERVICE_ACCOUNT_FILE`, or default `secrets/service-account.json` |
| `SPREADSHEET_ID` | Target spreadsheet |
| `RESPONSES_SHEET_NAME` / `RESULTS_SHEET_NAME` | Tab names (must match the spreadsheet exactly) |
| `WRITE_RESULTS_SHEET` | `true` = save a copy to Results after each assessment; `false` = skip |
| `EMAIL_COLUMN` / `PROCESSED_COLUMN` | Responses headers |
| `JOB_SET` | `core_30` (default) or `client_40` |
| `JOBS_FILE` | Optional override for structured job JSON |
| `TOP_K` | Ranked jobs returned (default `5`) |
| `USE_MOCK_SHEETS` | `true` = in-memory sample row; `false` = live Sheets |

`question_columns` defaults to **A1–F8** in `backend/config.py`. Override with comma-separated `QUESTION_COLUMNS` in `.env` if Tally exports different headers.

## Google Sheets layout

Two tabs in the **same** spreadsheet (`SPREADSHEET_ID`). Tab names in `.env` must match the labels at the **bottom** of the file exactly.

| Setting | Role |
|---------|------|
| `RESPONSES_SHEET_NAME` | **Input** — Tally (or CSV import) puts one row per respondent here. **Required** for live mode. |
| `RESULTS_SHEET_NAME` | **Optional archive** — backend can copy scores here after each run. **Not** used to load the results page. |
| `WRITE_RESULTS_SHEET` | `true` (default) = write/update Results; `false` = only read Responses (simpler setup). |

Flow: **Responses** → score + LLM → JSON to browser; optionally also append/update **Results**.

### Responses

Row 1 must include **`email`** and **`A1` … `F8`**. **`processed`** is optional. Answer cells use integers **0–4**.

Import helper: [data/sample_responses.csv](data/sample_responses.csv).

### Results (optional archive)

When `WRITE_RESULTS_SHEET=true` (default), the backend writes:

| Column | Content |
|--------|---------|
| `email` | Respondent email |
| `user_dimension_vector` | JSON object with six dimension means |
| `top_jobs` | JSON array of `job_id`, `job_label`, `score`, `reason` |
| `summary` | Short user-facing summary |

Legacy rows that store `job` instead of `job_label` are still read by the API.

## Job catalogs and sample data

| File | Use |
|------|-----|
| `data/jobs_30_core.json` | Default structured job catalog |
| `data/jobs_40_client.json` | Extended catalog target (`JOB_SET=client_40`); must be a valid jobs array before use |
| `data/benchmark_samples.json` | Six manual benchmark profiles |
| `data/test_answers.example.json` | Local answers template |
| `data/benchmark_results/scorer_core_30.json` | Latest scorer-only benchmark output |

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/api/results?email=&job_set=` | Run assessment; JSON: `email`, `user_dimension_vector`, `top_jobs`, `summary`, `job_set` |
| `GET` | `/results.html` | Results UI (`?email=` required; optional `job_set=core_30` or `client_40`) |

## Where to change behavior

| What | Where |
|------|--------|
| Explanation prompts | `backend/prompt_templates.py` |
| Python scoring and tie-breaks | `backend/scorer.py` |
| Job catalog loading | `backend/job_loader.py`, `JOBS_FILE`, `JOB_SET` |
| API and result shapes | `backend/models.py`, `backend/main.py` |
| Provider, models, sheet names | `.env`, `backend/config.py` |
| Sheet read/write | `backend/sheets_client.py` |
| Orchestration | `backend/scoring_engine.py` |
| Results UI | `frontend/results.html` |

## Tally redirect

On the thank-you screen, redirect to your deployed host, for example:

`https://your-domain.com/results.html?email={field:email}`

Use the correct merge tag for your email field.

## Deployment

Run `python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000` behind HTTPS (reverse proxy). Set environment variables on the host. Do not commit `.env`, API keys, or service account JSON.
