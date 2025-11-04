
#!/usr/bin/env python3
"""
Convenience script to run preflight tests.

Usage:
    python scripts/preflight/run_preflight.py              # Run all
    python scripts/preflight/run_preflight.py --smoke      # Smoke tests only
    python scripts/preflight/run_preflight.py --verbose    # Verbose output
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run preflight test suite."""
    
    # Build pytest command
    cmd = ['pytest', 'scripts/preflight/']
    
    # Parse simple arguments
    if '--smoke' in sys.argv:
        cmd.extend(['-m', 'smoke'])
    
    if '--verbose' in sys.argv or '-v' in sys.argv:
        cmd.append('-v')
    
    if '--coverage' in sys.argv:
        cmd.extend(['--cov=sologit', '--cov-report=term-missing'])
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    print("=" * 70)
    
    result = subprocess.run(cmd)
    
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
