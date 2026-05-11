"""
Send local test answers through the assessment pipeline.

Usage (from project root, with .env configured and venv activated):

  python scripts/try_llm.py
  python scripts/try_llm.py data/my_test_answers.json
  python scripts/try_llm.py --scores-only data/benchmark_samples.json

JSON format: either {"answers": {"A1": "0", ...}} or a flat object of A1..F8 values (0-4).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"


def _load_answers(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    answers = data.get("answers") if isinstance(data.get("answers"), dict) else data
    if not isinstance(answers, dict):
        raise ValueError('JSON must be {"answers": {...}} or a flat object of question→answer.')
    return {str(key): str(value) for key, value in answers.items() if str(value).strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local assessment or scorer-only checks.")
    parser.add_argument("answers_file", nargs="?", help="Path to answers JSON.")
    parser.add_argument(
        "--scores-only",
        action="store_true",
        help="Run Python scoring only and skip the LLM explanation step.",
    )
    args = parser.parse_args()

    path = Path(args.answers_file) if args.answers_file else ROOT / "data" / "test_answers.json"
    if not path.is_file():
        sys.stderr.write(
            f"Missing file: {path}\n"
            f"Copy data/test_answers.example.json to data/test_answers.json and edit it.\n"
        )
        sys.exit(1)

    answers_str = _load_answers(path)
    sys.path.insert(0, str(BACKEND_DIR))

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    if args.scores_only:
        from config import get_settings
        from job_loader import load_jobs
        from scorer import build_user_vector, rank_jobs

        settings = get_settings()
        vector = build_user_vector(answers_str)
        ranked = rank_jobs(vector, load_jobs(settings), top_k=settings.top_k)
        payload = {
            "user_dimension_vector": vector.model_dump(),
            "top_jobs": [job.model_dump() for job in ranked],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    from llm_service import call_assessment

    out = call_assessment(answers_str)
    print(out.model_dump_json(indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)
