# 93 — module entry point: `python3 -m vates_stratorvm ...` == the CLI.
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
