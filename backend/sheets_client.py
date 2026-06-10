"""Google Sheets I/O for the career test.

Responses tab (RESPONSES_SHEET_NAME): questionnaire input (email, A1–F8) — read on each assessment.
Results tab (RESULTS_SHEET_NAME): optional archive written after scoring when WRITE_RESULTS_SHEET=true.
The API does not read Results to serve /api/results; it always scores from Responses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from config import Settings, get_settings
from google_credentials import has_google_service_account_credentials, load_google_credentials
from models import AssessmentResult
from utils import normalize_email

MOCK_SAMPLE_1_ANSWERS: dict[str, str] = {
    "A1": "1",
    "A2": "2",
    "A3": "0",
    "A4": "0",
    "A5": "2",
    "A6": "3",
    "A7": "0",
    "A8": "0",
    "B1": "4",
    "B2": "4",
    "B3": "4",
    "B4": "4",
    "B5": "3",
    "B6": "3",
    "B7": "2",
    "B8": "2",
    "C1": "2",
    "C2": "2",
    "C3": "4",
    "C4": "4",
    "C5": "1",
    "C6": "1",
    "C7": "1",
    "C8": "1",
    "D1": "0",
    "D2": "0",
    "D3": "1",
    "D4": "1",
    "D5": "1",
    "D6": "0",
    "D7": "0",
    "D8": "0",
    "E1": "2",
    "E2": "2",
    "E3": "1",
    "E4": "2",
    "E5": "1",
    "E6": "2",
    "E7": "1",
    "E8": "1",
    "F1": "2",
    "F2": "3",
    "F3": "3",
    "F4": "3",
    "F5": "2",
    "F6": "2",
    "F7": "2",
    "F8": "2",
}


@dataclass
class ResponseRow:
    email: str
    answers: dict[str, str]
    row_number: int  # 1-based sheet row index
    processed_raw: str | None


class SheetsClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._gc = None

    def _client(self):
        if self.settings.use_mock_sheets:
            return None
        if self._gc is not None:
            return self._gc
        if not has_google_service_account_credentials(self.settings):
            raise RuntimeError(
                "Google Sheets credentials are not configured. Set GOOGLE_SERVICE_ACCOUNT_* values in .env, "
                "set GOOGLE_SERVICE_ACCOUNT_FILE to a JSON key file, or set USE_MOCK_SHEETS=true for local demo "
                "without Google Sheets."
            )
        if not self.settings.spreadsheet_id:
            raise RuntimeError("SPREADSHEET_ID is not set")

        import gspread

        creds = load_google_credentials(self.settings)
        self._gc = gspread.authorize(creds)
        return self._gc

    def _worksheet(self, sh, title: str):
        import gspread

        try:
            return sh.worksheet(title)
        except gspread.WorksheetNotFound as exc:
            available = [ws.title for ws in sh.worksheets()]
            raise RuntimeError(
                f'Worksheet "{title}" was not found in spreadsheet {self.settings.spreadsheet_id}. '
                f'Available tabs: {", ".join(available) if available else "(none)"}. '
                "Set RESPONSES_SHEET_NAME or RESULTS_SHEET_NAME in .env to match the tab name exactly."
            ) from exc

    def _responses_ws(self):
        gc = self._client()
        sh = gc.open_by_key(self.settings.spreadsheet_id)
        return self._worksheet(sh, self.settings.responses_sheet_name)

    def _results_headers(self) -> list[str]:
        return [
            self.settings.results_email_column,
            self.settings.results_job_set_column,
            self.settings.results_user_vector_column,
            self.settings.results_top_jobs_column,
            self.settings.results_summary_column,
        ]

    def _results_ws(self):
        gc = self._client()
        sh = gc.open_by_key(self.settings.spreadsheet_id)
        try:
            return sh.worksheet(self.settings.results_sheet_name)
        except Exception:
            ws = sh.add_worksheet(
                title=self.settings.results_sheet_name,
                rows=1000,
                cols=10,
            )
            ws.append_row(self._results_headers())
            return ws

    def _validate_response_headers(self, headers: list[str]) -> None:
        required = [self.settings.email_column, *self.settings.question_columns]
        missing = [name for name in required if name not in headers]
        if missing:
            raise RuntimeError(
                "Responses sheet row 1 is missing required headers: "
                + ", ".join(missing)
            )

    def list_response_rows(self) -> list[ResponseRow]:
        if self.settings.use_mock_sheets:
            return _mock_rows(self.settings)

        ws = self._responses_ws()
        rows = ws.get_all_values()
        if not rows:
            return []
        headers = [h.strip() for h in rows[0]]
        self._validate_response_headers(headers)

        email_col = self.settings.email_column
        proc_col = self.settings.processed_column
        qcols = self.settings.question_columns

        def idx(name: str) -> int:
            return headers.index(name)

        email_i = idx(email_col)
        q_indices = {q: idx(q) for q in qcols}
        proc_i = headers.index(proc_col) if proc_col in headers else None

        out: list[ResponseRow] = []
        for rnum, row in enumerate(rows[1:], start=2):
            if email_i >= len(row):
                continue
            email = (row[email_i] or "").strip()
            if not email:
                continue
            answers: dict[str, str] = {}
            for q, qi in q_indices.items():
                answers[q] = row[qi].strip() if qi < len(row) else ""
            proc_val = None
            if proc_i is not None and proc_i < len(row):
                proc_val = row[proc_i].strip().lower() or None
            out.append(ResponseRow(email=email, answers=answers, row_number=rnum, processed_raw=proc_val))
        return out

    def get_response_by_email(self, email: str) -> ResponseRow | None:
        """Latest row wins if the same email appears more than once."""
        target = normalize_email(email)
        last: ResponseRow | None = None
        for row in self.list_response_rows():
            if normalize_email(row.email) == target:
                last = row
        return last

    def append_response_row(self, email: str, answers: dict[str, str]) -> int:
        """Append one Responses row (used by the Tally webhook). Returns 1-based row index."""
        if self.settings.use_mock_sheets:
            return _mock_append_row(email, answers)

        ws = self._responses_ws()
        rows = ws.get_all_values()
        headers = [h.strip() for h in rows[0]] if rows else []

        if not headers:
            headers = [self.settings.email_column, *self.settings.question_columns]
            ws.append_row(headers)
            rows = ws.get_all_values()
            headers = [h.strip() for h in rows[0]]

        for name in [self.settings.email_column, *self.settings.question_columns]:
            if name not in headers:
                headers.append(name)
                ws.update_cell(1, len(headers), name)

        row_values = []
        for header in headers:
            if header == self.settings.email_column:
                row_values.append(email.strip())
            elif header in self.settings.question_columns:
                row_values.append(answers.get(header, ""))
            else:
                row_values.append("")

        ws.append_row(row_values)
        return len(rows) + 1

    def mark_processed(self, row_number: int, value: str = "TRUE") -> None:
        if self.settings.use_mock_sheets:
            _mock_mark_processed(row_number, value)
            return
        ws = self._responses_ws()
        headers = ws.row_values(1)
        try:
            col = headers.index(self.settings.processed_column) + 1
        except ValueError:
            col = len(headers) + 1
            ws.update_cell(1, col, self.settings.processed_column)
        ws.update_cell(row_number, col, value)

    def upsert_result(self, email: str, result: AssessmentResult) -> None:
        top_jobs = [job.model_dump() for job in result.top_jobs]
        payload_vector = json.dumps(result.user_dimension_vector.model_dump(), ensure_ascii=False)
        payload_top = json.dumps(top_jobs, ensure_ascii=False)
        summary = result.summary

        if self.settings.use_mock_sheets:
            _mock_save_result(self.settings, email, payload_vector, payload_top, summary)
            return

        job_set = self.settings.job_set

        ws = self._results_ws()
        rows = ws.get_all_values()
        headers = [h.strip() for h in rows[0]] if rows else []
        if not headers:
            headers = self._results_headers()
            ws.append_row(headers)
            rows = ws.get_all_values()
            headers = [h.strip() for h in rows[0]]

        for header in self._results_headers():
            if header not in headers:
                headers.append(header)
                ws.update_cell(1, len(headers), header)

        values_by_header = {
            self.settings.results_email_column: email,
            self.settings.results_job_set_column: job_set,
            self.settings.results_user_vector_column: payload_vector,
            self.settings.results_top_jobs_column: payload_top,
            self.settings.results_summary_column: summary,
        }

        email_col_idx = headers.index(self.settings.results_email_column)
        job_set_col_idx = (
            headers.index(self.settings.results_job_set_column)
            if self.settings.results_job_set_column in headers
            else None
        )
        email_norm = normalize_email(email)
        row_idx: int | None = None
        for i, row in enumerate(rows[1:], start=2):
            if not row:
                continue
            padded = list(row) + [""] * (len(headers) - len(row))
            if normalize_email(padded[email_col_idx]) != email_norm:
                continue
            if job_set_col_idx is not None:
                stored_job_set = padded[job_set_col_idx].strip() or "core_30"
                if stored_job_set != job_set:
                    continue
            row_idx = i
            break

        if row_idx is None:
            new_row = [values_by_header.get(h, "") for h in headers]
            ws.append_row(new_row)
        else:
            for c, h in enumerate(headers, start=1):
                ws.update_cell(row_idx, c, values_by_header.get(h, ""))

def _parse_result_row(row: list[str], headers: list[str], settings: Settings) -> dict[str, Any]:
    def cell(name: str) -> str:
        index = headers.index(name)
        return row[index] if index < len(row) else ""

    top_jobs_raw = json.loads(cell(settings.results_top_jobs_column))
    top_jobs = [_normalize_top_job(item) for item in top_jobs_raw]
    data: dict[str, Any] = {
        "email": cell(settings.results_email_column),
        "top_jobs": top_jobs,
        "summary": cell(settings.results_summary_column),
    }

    vector_column = settings.results_user_vector_column
    if vector_column in headers and cell(vector_column):
        data["user_dimension_vector"] = json.loads(cell(vector_column))

    job_set_column = settings.results_job_set_column
    if job_set_column in headers and cell(job_set_column):
        data["job_set"] = cell(job_set_column)
    else:
        data["job_set"] = settings.job_set

    return data


def _normalize_top_job(item: dict[str, Any]) -> dict[str, Any]:
    if "job_label" in item:
        return {
            "job_id": item.get("job_id", ""),
            "job_label": item["job_label"],
            "score": item.get("score", 0),
            "reason": item.get("reason", ""),
        }
    if "job" in item:
        return {
            "job_id": item.get("job_id", ""),
            "job_label": item["job"],
            "score": item.get("score", 0),
            "reason": item.get("reason", ""),
        }
    raise ValueError("top_jobs entry must include job_label or job")


# --- mock store for local dev ---

_MOCK_STORE: dict[str, dict[str, Any]] = {}
_MOCK_ROWS_STATE: list[ResponseRow] | None = None


def _mock_rows(settings: Settings) -> list[ResponseRow]:
    global _MOCK_ROWS_STATE
    if _MOCK_ROWS_STATE is None:
        answers = {key: value for key, value in MOCK_SAMPLE_1_ANSWERS.items()}
        _MOCK_ROWS_STATE = [
            ResponseRow(
                email="demo@example.com",
                answers=answers,
                row_number=2,
                processed_raw=None,
            )
        ]
    return _MOCK_ROWS_STATE


def _mock_append_row(email: str, answers: dict[str, str]) -> int:
    global _MOCK_ROWS_STATE
    if _MOCK_ROWS_STATE is None:
        _mock_rows(get_settings())
    assert _MOCK_ROWS_STATE is not None
    row_number = max((row.row_number for row in _MOCK_ROWS_STATE), default=1) + 1
    _MOCK_ROWS_STATE.append(
        ResponseRow(
            email=email.strip(),
            answers={key: str(value) for key, value in answers.items()},
            row_number=row_number,
            processed_raw=None,
        )
    )
    return row_number


def _mock_mark_processed(row_number: int, value: str) -> None:
    global _MOCK_ROWS_STATE
    if _MOCK_ROWS_STATE is None:
        return
    for row in _MOCK_ROWS_STATE:
        if row.row_number == row_number:
            row.processed_raw = value.strip().lower()
            break


def _mock_result_key(email: str, job_set: str) -> str:
    return f"{normalize_email(email)}|{job_set}"


def _mock_save_result(
    settings: Settings,
    email: str,
    user_vector_json: str,
    top_jobs_json: str,
    summary: str,
) -> None:
    top_jobs = json.loads(top_jobs_json)
    _MOCK_STORE[_mock_result_key(email, settings.job_set)] = {
        "email": email,
        "job_set": settings.job_set,
        "user_dimension_vector": json.loads(user_vector_json),
        "top_jobs": [_normalize_top_job(item) for item in top_jobs],
        "summary": summary,
    }


