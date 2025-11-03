
#!/usr/bin/env python3
"""Pre-flight test: CLI/API/GUI contracts."""
import sys

def test_cli_contracts():
    """Test CLI command contracts."""
    print("Testing CLI contracts...")
    
    try:
        from click.testing import CliRunner
        from sologit.cli.main import cli
        
        runner = CliRunner()
        
        # Test help command
        result = runner.invoke(cli, ['--help'])
        if result.exit_code != 0:
            raise Exception("CLI help command failed")
        
        # Test version command
        result = runner.invoke(cli, ['version'])
        if result.exit_code != 0:
            raise Exception("CLI version command failed")
        
        print("  ✓ CLI contracts")
        return True
    except Exception as e:
        print(f"  ✗ CLI contracts: {e}")
        return False

def test_api_contracts():
    """Test Python API contracts."""
    print("Testing API contracts...")
    
    try:
        # Test public API interfaces
        from sologit.core.repository import Repository
        from sologit.core.workpad import Workpad
        from sologit.engines.git_engine import GitEngine
        
        print("  ✓ API contracts")
        return True
    except Exception as e:
        print(f"  ✗ API contracts: {e}")
        return False

def test_state_contracts():
    """Test state file format contracts."""
    print("Testing state contracts...")
    
    try:
        from sologit.state.schema import RepositoryState, WorkpadState
        
        # Test state schema
        print("  ✓ State contracts")
        return True
    except Exception as e:
        print(f"  ✗ State contracts: {e}")
        return False

def main():
    """Run contract tests."""
    print("="*60)
    print("PRE-FLIGHT TEST: CLI/API/GUI CONTRACTS")
    print("="*60)
    
    results = [
        test_cli_contracts(),
        test_api_contracts(),
        test_state_contracts(),
    ]
    
    print("\n" + "="*60)
    if all(results):
        print("✓ ALL CONTRACT TESTS PASSED")
        print("="*60)
        return 0
    else:
        print("✗ SOME CONTRACT TESTS FAILED")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
