"""
Run the brand-name-check example end to end.

    python examples/brand-name-check/run.py Lumen --category "desk lamp"

Needs GEMINI_API_KEY (or OPENAI_API_KEY for the GPT-4o fallback). Nothing is
written to a database; task outputs are printed.
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # repo root, so crewai_service imports

from crewai_service.crew import CrewBuilder, kickoff_and_get_results  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a product name against the brand guideline")
    parser.add_argument("product_name")
    parser.add_argument("--category", default="household product")
    args = parser.parse_args()

    inputs = {"product_name": args.product_name, "category": args.category}
    builder = CrewBuilder(config_dir=str(HERE / "config"))
    crew = builder.build_crew("brand_name_check", inputs)
    results = kickoff_and_get_results(crew, inputs)

    for i, task in enumerate(results["task_outputs"], start=1):
        print(f"\n{'=' * 70}\nTask {i} — {task['agent_role']}\n{'=' * 70}\n{task['result']}")


if __name__ == "__main__":
    main()
