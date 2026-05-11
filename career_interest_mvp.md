# Career interest test MVP (legacy notes)

This file describes the original MVP scope. The running application now follows **manual template v2**:

- 48-item questionnaire (**A1–F8**)
- Python ranking on six job dimensions
- LLM explanations only
- API and Sheets output with **top 5** jobs, `user_dimension_vector`, and `summary`

Use these documents instead of this file for current behavior:

- [README.md](README.md) — setup, Sheets layout, API, and local run
- [docs/MANUAL_CHATGPT_PROMPT_TEMPLATE.md](docs/MANUAL_CHATGPT_PROMPT_TEMPLATE.md) — scoring and prompt contract
- [docs/MIGRATION_TODO.md](docs/MIGRATION_TODO.md) — implementation checklist and architecture notes

---

## Original MVP overview

Users complete a Tally form, responses land in Google Sheets, a Python backend processes each row, and a simple web page shows career matches.

Original flow:

1. User submits the Tally form
2. Python reads Google Sheets
3. Backend builds results
4. Structured JSON is stored
5. Frontend displays results

The early MVP assumed short answer columns such as `Q1`, `Q2`, `Q3` and an LLM-driven job list. That path is superseded by the v2 pipeline documented in the README.
