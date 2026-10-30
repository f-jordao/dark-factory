"""Run one Fabro review, validate its response, and cancel on interruption."""

import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: run_fabro_review.py INPUT_JSON OUTPUT_JSON")
    project = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project))
    from dark_factory.fabro import LocalFabro
    timeout = int(os.environ.get("DARK_FACTORY_REVIEW_TIMEOUT_SECONDS", "850"))
    LocalFabro(project, timeout=timeout).review(sys.argv[1], sys.argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
