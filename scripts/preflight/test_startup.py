
#!/usr/bin/env python3
"""Pre-flight test: Startup and initialization."""
import sys
import importlib
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")
    
    modules = [
        "sologit",
        "sologit.cli",
        "sologit.core",
        "sologit.engines",
        "sologit.orchestration",
        "sologit.workflows",
        "sologit.state",
        "sologit.config",
        "sologit.api",
        "sologit.ui",
        "sologit.utils",
        "sologit.analysis",
    ]
    
    failures = []
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"  ✓ {module}")
        except Exception as e:
            print(f"  ✗ {module}: {e}")
            failures.append((module, str(e)))
    
    if failures:
        print(f"\n✗ Import failures: {len(failures)}")
        return False
    else:
        print(f"\n✓ All modules imported successfully")
        return True

def test_cli_entry_point():
    """Test CLI entry point."""
    print("\nTesting CLI entry point...")
    
    try:
        from sologit.cli.main import cli
        print("  ✓ CLI entry point accessible")
        return True
    except Exception as e:
        print(f"  ✗ CLI entry point failed: {e}")
        return False

def test_config_loading():
    """Test configuration loading."""
    print("\nTesting configuration loading...")
    
    try:
        from sologit.config.manager import ConfigManager
        manager = ConfigManager()
        print("  ✓ ConfigManager initialized")
        return True
    except Exception as e:
        print(f"  ✗ ConfigManager failed: {e}")
        return False

def main():
    """Run startup tests."""
    print("="*60)
    print("PRE-FLIGHT TEST: STARTUP AND INITIALIZATION")
    print("="*60)
    
    results = [
        test_imports(),
        test_cli_entry_point(),
        test_config_loading(),
    ]
    
    print("\n" + "="*60)
    if all(results):
        print("✓ ALL STARTUP TESTS PASSED")
        print("="*60)
        return 0
    else:
        print("✗ SOME STARTUP TESTS FAILED")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
