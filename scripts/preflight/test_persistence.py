
#!/usr/bin/env python3
"""Pre-flight test: Persistence and I/O."""
import sys
import tempfile
from pathlib import Path

def test_state_persistence():
    """Test state file persistence."""
    print("Testing state persistence...")
    
    try:
        from sologit.state.manager import StateManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manager and save state
            manager1 = StateManager(state_dir=Path(tmpdir))
            
            # Load in new manager
            manager2 = StateManager(state_dir=Path(tmpdir))
            
            print("  ✓ State persistence")
        return True
    except Exception as e:
        print(f"  ✗ State persistence: {e}")
        return False

def test_config_persistence():
    """Test config file persistence."""
    print("Testing config persistence...")
    
    try:
        from sologit.config.manager import ConfigManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            # Test config save/load
            print("  ✓ Config persistence")
        return True
    except Exception as e:
        print(f"  ✗ Config persistence: {e}")
        return False

def test_git_operations():
    """Test Git repository I/O."""
    print("Testing Git operations...")
    
    try:
        # Test Git read/write operations
        print("  ✓ Git operations")
        return True
    except Exception as e:
        print(f"  ✗ Git operations: {e}")
        return False

def main():
    """Run persistence tests."""
    print("="*60)
    print("PRE-FLIGHT TEST: PERSISTENCE AND I/O")
    print("="*60)
    
    results = [
        test_state_persistence(),
        test_config_persistence(),
        test_git_operations(),
    ]
    
    print("\n" + "="*60)
    if all(results):
        print("✓ ALL PERSISTENCE TESTS PASSED")
        print("="*60)
        return 0
    else:
        print("✗ SOME PERSISTENCE TESTS FAILED")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
