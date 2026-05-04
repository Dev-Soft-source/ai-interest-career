"""
Send local test answers to the configured LLM (same pipeline as production).

Usage (from project root, with .env configured and venv activated):

  python scripts/try_llm.py
  python scripts/try_llm.py data/my_test_answers.json

JSON format: either {"answers": {"Q1": "...", "Q2": "..."}} or a flat {"Q1": "..."}.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "test_answers.json"

    if not path.is_file():
        sys.stderr.write(
            f"Missing file: {path}\n"
            f"Copy data/test_answers.example.json to data/test_answers.json and edit it.\n"
        )
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    answers = data.get("answers") if isinstance(data.get("answers"), dict) else data
    if not isinstance(answers, dict):
        sys.stderr.write('JSON must be {"answers": {...}} or a flat object of question→answer.\n')
        sys.exit(1)

    answers_str = {str(k): str(v) for k, v in answers.items() if str(v).strip()}

    # Ensure backend imports resolve when run as script
    sys.path.insert(0, str(ROOT))

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    from backend.llm_service import call_llm

    out = call_llm(answers_str)
    print(out.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
