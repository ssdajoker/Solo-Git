
"""
Preflight self-test suite for Solo-Git.

This package contains pre-flight checks that verify all documented features
are working correctly before deployment or after major changes.

The preflight suite is designed to:
1. Test all documented features from the user perspective
2. Catch regressions quickly
3. Validate the system is ready for use
4. Provide fast feedback (< 60 seconds for full suite)

Usage:
    # Run all preflight tests
    python -m pytest scripts/preflight/

    # Run specific test module
    python -m pytest scripts/preflight/test_core_features.py

    # Run with verbose output
    python -m pytest scripts/preflight/ -v
"""

__version__ = "1.0.0"
