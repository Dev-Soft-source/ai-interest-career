"""Read Tally responses and write career results to Google Sheets."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from backend.config import Settings, get_settings
from backend.utils import normalize_email

logger = logging.getLogger(__name__)


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
        if not self.settings.google_service_account_file:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE is not set (or enable USE_MOCK_SHEETS=true)")
        if not self.settings.spreadsheet_id:
            raise RuntimeError("SPREADSHEET_ID is not set")

        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_file(
            self.settings.google_service_account_file,
            scopes=scopes,
        )
        self._gc = gspread.authorize(creds)
        return self._gc

    def _responses_ws(self):
        gc = self._client()
        sh = gc.open_by_key(self.settings.spreadsheet_id)
        return sh.worksheet(self.settings.responses_sheet_name)

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
            headers = [
                self.settings.results_email_column,
                self.settings.results_top_jobs_column,
                self.settings.results_scores_column,
                self.settings.results_summary_column,
            ]
            ws.append_row(headers)
            return ws

    def list_response_rows(self) -> list[ResponseRow]:
        if self.settings.use_mock_sheets:
            return _mock_rows(self.settings)

        ws = self._responses_ws()
        rows = ws.get_all_values()
        if not rows:
            return []
        headers = [h.strip() for h in rows[0]]
        email_col = self.settings.email_column
        proc_col = self.settings.processed_column
        qcols = self.settings.question_columns

        def idx(name: str) -> int | None:
            try:
                return headers.index(name)
            except ValueError:
                return None

        email_i = idx(email_col)
        if email_i is None:
            raise RuntimeError(f'Responses sheet must include column "{email_col}"')

        q_indices = {}
        for q in qcols:
            qi = idx(q)
            if qi is not None:
                q_indices[q] = qi
        proc_i = idx(proc_col)

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
        for r in self.list_response_rows():
            if normalize_email(r.email) == target:
                last = r
        return last

    def mark_processed(self, row_number: int, value: str = "TRUE") -> None:
        if self.settings.use_mock_sheets:
            return
        ws = self._responses_ws()
        headers = ws.row_values(1)
        try:
            col = headers.index(self.settings.processed_column) + 1
        except ValueError:
            col = len(headers) + 1
            ws.update_cell(1, col, self.settings.processed_column)
        ws.update_cell(row_number, col, value)

    def upsert_result(
        self,
        email: str,
        top_jobs: list[dict[str, Any]],
        scores: dict[str, int],
        summary: str,
    ) -> None:
        payload_top = json.dumps(top_jobs, ensure_ascii=False)
        payload_scores = json.dumps(scores, ensure_ascii=False)

        if self.settings.use_mock_sheets:
            _mock_save_result(self.settings, email, payload_top, payload_scores, summary)
            return

        ws = self._results_ws()
        rows = ws.get_all_values()
        ec = self.settings.results_email_column
        tc = self.settings.results_top_jobs_column
        sc = self.settings.results_scores_column
        smc = self.settings.results_summary_column
        default_headers = [ec, tc, sc, smc]

        if not rows:
            ws.append_row(default_headers)
            rows = ws.get_all_values()

        headers = [h.strip() for h in rows[0]]
        missing = [h for h in default_headers if h not in headers]
        if missing:
            raise RuntimeError(
                f'Results sheet row 1 must include columns {default_headers}. Missing: {missing}'
            )

        def header_to_idx(name: str) -> int:
            return headers.index(name)

        values_by_header = {
            ec: email,
            tc: payload_top,
            sc: payload_scores,
            smc: summary,
        }

        email_col_idx = header_to_idx(ec)
        email_norm = normalize_email(email)
        row_idx: int | None = None
        for i, row in enumerate(rows[1:], start=2):
            if not row:
                continue
            padded = list(row) + [""] * (len(headers) - len(row))
            if normalize_email(padded[email_col_idx]) == email_norm:
                row_idx = i
                break

        if row_idx is None:
            new_row = [values_by_header.get(h, "") for h in headers]
            ws.append_row(new_row)
        else:
            for c, h in enumerate(headers, start=1):
                ws.update_cell(row_idx, c, values_by_header.get(h, ""))

    def get_result_by_email(self, email: str) -> dict[str, Any] | None:
        if self.settings.use_mock_sheets:
            return _mock_get_result(self.settings, email)

        ws = self._results_ws()
        rows = ws.get_all_values()
        if len(rows) < 2:
            return None
        headers = [h.strip() for h in rows[0]]
        target = normalize_email(email)

        def col(name: str) -> int:
            return headers.index(name)

        ei = col(self.settings.results_email_column)
        for row in rows[1:]:
            if not row:
                continue
            while len(row) <= ei:
                row.append("")
            if normalize_email(row[ei]) != target:
                continue
            data: dict[str, Any] = {}
            try:
                data["email"] = row[col(self.settings.results_email_column)]
                data["top_jobs"] = json.loads(row[col(self.settings.results_top_jobs_column)])
                data["scores"] = json.loads(row[col(self.settings.results_scores_column)])
                data["summary"] = row[col(self.settings.results_summary_column)]
            except (ValueError, IndexError, json.JSONDecodeError) as e:
                logger.warning("Bad results row for %s: %s", email, e)
                return None
            return data
        return None


# --- mock store for local dev ---

_MOCK_STORE: dict[str, dict[str, Any]] = {}
_MOCK_ROWS_STATE: list[ResponseRow] | None = None


def _mock_rows(settings: Settings) -> list[ResponseRow]:
    global _MOCK_ROWS_STATE
    if _MOCK_ROWS_STATE is None:
        _MOCK_ROWS_STATE = [
            ResponseRow(
                email="demo@example.com",
                answers={"Q1": "A", "Q2": "B", "Q3": "C"},
                row_number=2,
                processed_raw=None,
            )
        ]
    return _MOCK_ROWS_STATE


def _mock_save_result(
    settings: Settings,
    email: str,
    top_jobs_json: str,
    scores_json: str,
    summary: str,
) -> None:
    _MOCK_STORE[normalize_email(email)] = {
        "email": email,
        "top_jobs": json.loads(top_jobs_json),
        "scores": json.loads(scores_json),
        "summary": summary,
    }


def _mock_get_result(settings: Settings, email: str) -> dict[str, Any] | None:
    return _MOCK_STORE.get(normalize_email(email))
