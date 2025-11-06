"""Run the Solo Git mock headless FastAPI service for local e2e CLI tests.

This starts the FastAPI app defined in sologit.headless_core on 127.0.0.1:1234
so the headless-backed CLI commands can connect during manual runs.

Usage (PowerShell):
  python scripts/run_headless_mock.py
"""
from __future__ import annotations

import uvicorn

from sologit.headless_core import app


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=1234, log_level="info")


if __name__ == "__main__":
    main()
