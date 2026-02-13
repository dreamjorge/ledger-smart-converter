#!/usr/bin/env python3

import sys
from pathlib import Path


def _bootstrap_src_path() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    _bootstrap_src_path()
    from db_pipeline import main as pipeline_main

    return pipeline_main()


if __name__ == "__main__":
    raise SystemExit(main())
