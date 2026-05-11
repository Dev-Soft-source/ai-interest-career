# Migration TODO — Manual Prompt Template v2

Align the running application with [MANUAL_CHATGPT_PROMPT_TEMPLATE.md](./MANUAL_CHATGPT_PROMPT_TEMPLATE.md): 48-item questionnaire (A1–F8), six-dimension job vectors, numeric ranking lock, `top_5` output, and strict JSON contract.

**Reference data:** `data/jobs_30_core.json`, `data/jobs_40_client.json`, `data/sample_responses_row2_sample1.csv`

---

## 1. Scope and decisions (locked)

| Decision | Choice |
|----------|--------|
| Product contract | **Manual template v2** (48 items A1–F8, six dimensions, structured job vectors) |
| Ranking | **(A) Python** — user vector, mean-distance scores, and tie-breaks in code; LLM generates explanations only |
| User-facing output | **`top_5`** with per-job **explanation** (`reason`) plus a short **summary** |

**Persistence:** store `user_dimension_vector`, `top_5` (with scores and reasons), and `summary` for API and Results sheet. Do not expose a full per-job score map on the results page.

**Runtime stack (locked):** questionnaire answers from **Google Sheets**; **Gemini** (`GEMINI_API_KEY`) for explanation text only after Python ranking.

---

## Reference — Google Sheets input + Gemini

### End-to-end flow (target)

```mermaid
flowchart LR
  Tally[Tally form] --> Responses[Google Sheets Responses]
  Responses --> Read[sheets_client list_response_rows]
  Read --> Score[Python scorer top_5]
  Score --> Gemini[Gemini explanations + summary]
  Gemini --> Results[Google Sheets Results]
  Results --> API[GET /api/results]
  API --> UI[Results page]
```

1. **Responses** tab: one row per respondent (`email`, **A1–F8** as integers 0–4, `processed`).
2. **`POST /api/process`** (or the results page on first load): `SheetsClient` reads unprocessed rows (`backend/sheets_client.py`).
3. **Python** builds the user dimension vector, scores jobs from `JOBS_FILE` (e.g. `data/jobs_30_core.json`), applies tie-breaks, selects **top 5** (per [MANUAL_CHATGPT_PROMPT_TEMPLATE.md](./MANUAL_CHATGPT_PROMPT_TEMPLATE.md)).
4. **Gemini** receives ranked jobs + profile context and returns JSON with **`reason`** per job and **`summary`** only (`backend/llm_service.py`, `LLM_PROVIDER=gemini`).
5. **Results** tab + API: persist and serve `user_dimension_vector`, `top_5`, `summary`; set **`processed`** to `TRUE` on the response row.

### `.env` (Sheets + Gemini)

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER=gemini` | Route explanation calls to Gemini |
| `GEMINI_API_KEY` | API key (required when provider is gemini) |
| `GEMINI_MODEL` | e.g. `gemini-1.5-flash` |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Service account JSON path |
| `SPREADSHEET_ID` | Target spreadsheet |
| `RESPONSES_SHEET_NAME` / `RESULTS_SHEET_NAME` | Tab names (default `Responses` / `Results`) |
| `EMAIL_COLUMN` / `PROCESSED_COLUMN` | Usually `email` / `processed` |
| `JOBS_FILE` | Structured job list (target: `data/jobs_30_core.json`) |
| `USE_MOCK_SHEETS=true` | Local dev without Sheets (still needs `GEMINI_API_KEY`) |

`question_columns` must list every answer header the sheet exports (**A1–F8** after migration). Defaults today are still **Q1–Q3** in `backend/config.py` until that todo is done.

### Sheet layout and sample data

- Import template: `data/sample_responses_row2_sample1.csv` (Sample 1 profile from the manual doc).
- Benchmark answers: manual template **section 5** (six profiles).
- Job vectors: `data/jobs_30_core.json`, `data/jobs_40_client.json`.

### Code touchpoints

| Step | Module |
|------|--------|
| Read / write Sheets | `backend/sheets_client.py` |
| Orchestration | `backend/scoring_engine.py` |
| Gemini call | `backend/llm_service.py` (`_call_gemini`) |
| Settings | `backend/config.py`, `.env` |
| HTTP API | `backend/main.py` |

### Today vs target

| Area | Today | Target |
|------|--------|--------|
| Sheet columns | `Q1`, `Q2`, `Q3` | `A1`–`F8` |
| Ranking | Gemini scores all jobs in one call | Python ranks; Gemini explains top 5 |
| Jobs input | String list via `load_job_list()` | Structured JSON with 6D vectors |
| API output | `top_jobs` (3), `scores` map | `top_5` with the reason, `summary`|

---

## 2. Configuration and job data

- [x] Replace string-based `load_job_list()` with structured jobs (`job_id`, `job_label`, `scores`, `short_description`).
- [x] Default `JOBS_FILE` to `data/jobs_30_core.json`; support switching to `data/jobs_40_client.json`.
- [x] Add settings for `top_k` (fixed at **5** unless overridden for testing), job set selection, and optional core whitelist.
- [x] Default `question_columns` to **A1–F8** (48 columns); document Tally → Sheets header mapping.
- [x] Extend `.env.example` with new variables (job file, columns, `top_k`, flags).

---

## 3. Prompts and models

- [x] Add LLM prompts for **explanation-only** use (summary + `top_5` reasons), aligned with manual template semantics; do not ask the model to compute or reorder ranks.
- [x] Build user prompt payload from ranked `top_5`, user vector, item-level answers, and job `short_description` context.
- [x] Redefine Pydantic models in `backend/models.py`:
  - [x] `user_dimension_vector` (six canonical keys)
  - [x] `top_5` entries: `job_id`, `job_label`, `score`, `reason`
  - [x] `summary`
- [x] Add Python scorer module (user vector from items, distance formula, rounding, tie-break) and run it **before** the LLM explanation step.

---

## 4. Google Sheets pipeline

- [x] Validate Responses rows: 48 keys in 0–4; clear errors for missing or invalid cells.
- [x] Expand Results storage for v2 fields (vector, `top_5` with reasons, `summary`).
- [x] Update mock Sheets sample to A1–F8 (e.g. Sample 1 from the manual doc), not Q1–Q3.
- [x] Confirm Tally export headers match `email`, `A1`–`F8`, `processed`.

---

## 5. API and orchestration

- [x] Update `backend/scoring_engine.py` for new answer shape, job payload, and persistence.
- [x] Update `backend/llm_service.py` to call the scorer first, then request explanations and summary from the LLM.
- [x] Update `backend/main.py` — `GET /api/results` returns v2 shape; decide backward compatibility for old Results rows.
- [x] Tune LLM settings for explanation generation (JSON mode where supported; low temperature).

---

## 6. Frontend

- [x] Fix results route: serve `frontend/index.html` as `results.html` or update routes and README.
- [x] Display **top 5** with `job_label`, `score`, and `reason` and `summary`.

---

## 7. Testing and QA

- [x] Unit tests: user vector, distance formula, tie-break, answer parsing (manual section 5 samples).
- [x] Integration tests: mock Sheets + mocked LLM through `POST /api/process` and `GET /api/results`.
- [x] Update `scripts/try_llm.py` for A1–F8 fixtures and v2 JSON output.
- [x] Run benchmark: 6 samples × 2 job files; apply section 6 pass/fail table; save raw JSON and A/B notes (section 4).
- [x] Cross-model check (OpenAI vs Gemini): explanation quality and JSON validity (ranking is identical because Python scores jobs).

---

## 8. Documentation

- [x] Update `README.md`: v2 flow, sheet layout, job files, env vars; fix local run path (repo root, not `cd Career`).
- [x] Update or supersede `career_interest_mvp.md` with a pointer to the manual template.
- [x] Keep `docs/SYSTEM_PROMPT_REPORT.txt` aligned after implementation.
- [x] Maintain sample CSV/JSON under `data/` for import and local runs.

---

## Suggested order

1. Config + job loader + models  
2. Python scorer + explanation prompts  
3. Sheets + API + orchestration  
4. Frontend  
5. Tests + six-sample benchmark  
6. README and `.env.example`
