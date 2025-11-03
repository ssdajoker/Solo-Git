#!/bin/bash
set -euo pipefail

pytest --cov=sologit \
  --cov-report=term-missing \
  --cov-report=html:coverage_html \
  --cov-report=json:coverage.json \
  tests_phase2/

python3 <<'PY'
import json
from pathlib import Path

coverage_path = Path('coverage.json')
if not coverage_path.exists():
    raise SystemExit('coverage.json not found')

with coverage_path.open() as f:
    data = json.load(f)

print('\n🔍 Files Below 95% Coverage:\n')
for file, stats in sorted(data.get('files', {}).items()):
    pct = stats.get('summary', {}).get('percent_covered', 0.0)
    if pct < 95:
        missing = stats.get('missing_lines', [])
        print(f"{file}: {pct:.1f}% ({len(missing)} lines uncovered)")
PY
