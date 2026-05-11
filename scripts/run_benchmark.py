"""
Run deterministic scorer benchmarks for the six manual test profiles.

Usage (from project root, with venv activated):

  python scripts/run_benchmark.py
  python scripts/run_benchmark.py --job-set client_40
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scorer benchmark profiles.")
    parser.add_argument(
        "--job-set",
        choices=("core_30", "client_40"),
        default="core_30",
        help="Job catalog to score against.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "data" / "benchmark_results"),
        help="Directory for JSON benchmark output.",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(BACKEND_DIR))
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    from config import Settings, get_settings
    from job_loader import load_jobs
    from scorer import build_user_vector, rank_jobs

    get_settings.cache_clear()
    settings = Settings(job_set=args.job_set)
    samples = json.loads((ROOT / "data" / "benchmark_samples.json").read_text(encoding="utf-8"))
    jobs = load_jobs(settings)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"scorer_{args.job_set}.json"

    report: dict[str, object] = {
        "job_set": args.job_set,
        "job_count": len(jobs),
        "samples": {},
    }

    for sample_name, answers in samples.items():
        vector = build_user_vector(answers)
        ranked = rank_jobs(vector, jobs, top_k=settings.top_k)
        report["samples"][sample_name] = {
            "user_dimension_vector": vector.model_dump(),
            "top_jobs": [job.model_dump() for job in ranked],
        }

    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"Benchmark failed: {exc}\n")
        sys.exit(1)
