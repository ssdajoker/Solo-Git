"""
Solo-Git sidecar entrypoint.

This binary is bundled with the Heaven GUI as an external sidecar.
It exposes the CLI so the GUI can invoke operations without requiring a
system Python install.

Usage examples (invoked by GUI via Tauri Shell sidecar):
  sologit-core --version
  sologit-core repo list
  sologit-core commit-msg --help
"""
from __future__ import annotations

import sys
from typing import List


def main(argv: List[str] | None = None) -> int:
    import click
    from sologit.cli.main import cli

    try:
        args = list(argv) if argv is not None else sys.argv[1:]
        if not args:
            args = ["--help"]
        return cli.main(args=args, standalone_mode=False) or 0
    except click.Abort:
        return 1
    except SystemExit as e:
        return int(getattr(e, "code", 1) or 1)
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"sologit-core error: {e}\n")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
