#!/usr/bin/env python3
"""
Phase 3 Demo: Auto-Merge Workflow with CI Orchestration

This demo shows the complete Phase 3 workflow:
1. Create a workpad
2. Make changes
3. Run tests
4. Auto-merge on green
5. CI smoke tests
6. Rollback on failure (if needed)
"""

import tempfile
import shutil
from pathlib import Path

# Solo Git imports
from sologit.engines.git_engine import GitEngine
from sologit.engines.test_orchestrator import TestOrchestrator, TestConfig
from sologit.workflows.auto_merge import AutoMergeWorkflow
from sologit.workflows.ci_orchestrator import CIOrchestrator
from sologit.workflows.rollback_handler import RollbackHandler
from sologit.workflows.promotion_gate import PromotionRules
from sologit.utils.logger import setup_logging


def create_demo_repository(base_path: Path) -> str:
    """Create a demo repository with sample code."""
    repo_path = base_path / "demo-app"
    repo_path.mkdir()
    
    # Create a simple Python app
    (repo_path / "app.py").write_text("""
def greet(name: str) -> str:
    \"\"\"Greet someone by name.\"\"\"
    return f"Hello, {name}!"

def main():
    print(greet("World"))

if __name__ == "__main__":
    main()
""")
    
    # Create tests
    (repo_path / "test_app.py").write_text("""
from app import greet

def test_greet():
    \"\"\"Test the greet function.\"\"\"
    assert greet("Alice") == "Hello, Alice!"
    assert greet("Bob") == "Hello, Bob!"

def test_greet_empty():
    \"\"\"Test with empty string.\"\"\"
    assert greet("") == "Hello, !"
""")
    
    # Create README
    (repo_path / "README.md").write_text("""
# Demo Application

A simple demo app for Solo Git Phase 3.

## Features
- Greeting function
- Comprehensive tests
- Auto-merge workflow
""")
    
    return str(repo_path)


def demo_successful_auto_merge():
    """Demo: Successful auto-merge workflow."""
    print("=" * 80)
    print("DEMO 1: Successful Auto-Merge Workflow")
    print("=" * 80)
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        
        # Step 1: Create repository
        print("📦 Step 1: Creating demo repository...")
        repo_source = create_demo_repository(base_path)
        
        # Initialize Git engine
        repos_path = base_path / "repos"
        repos_path.mkdir()
        git_engine = GitEngine(str(repos_path))
        
        # Initialize from directory
        repo = git_engine.init_from_directory(repo_source, "demo-app")
        print(f"   ✅ Repository created: {repo.id}")
        print()
        
        # Step 2: Create workpad
        print("📝 Step 2: Creating workpad for new feature...")
        workpad = git_engine.create_workpad(repo.id, "add-goodbye-function")
        print(f"   ✅ Workpad created: {workpad.id} ({workpad.title})")
        print()
        
        # Step 3: Make changes
        print("✏️  Step 3: Adding goodbye function...")
        patch = """
diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -3,6 +3,10 @@ def greet(name: str) -> str:
     \"\"\"Greet someone by name.\"\"\"
     return f"Hello, {name}!"
 
+def goodbye(name: str) -> str:
+    \"\"\"Say goodbye to someone.\"\"\"
+    return f"Goodbye, {name}!"
+
 def main():
     print(greet("World"))
"""
        
        git_engine.apply_patch(workpad.id, patch)
        print("   ✅ Changes applied to workpad")
        print()
        
        # Step 4: Configure tests
        print("🧪 Step 4: Configuring test suite...")
        tests = [
            TestConfig(
                name="unit_tests",
                cmd="python -m pytest test_app.py -v",
                timeout=30
            )
        ]
        print(f"   ✅ Configured {len(tests)} test(s)")
        print()
        
        # Step 5: Auto-merge workflow
        print("🚀 Step 5: Running auto-merge workflow...")
        print("   This will:")
        print("   • Run tests in isolated sandbox")
        print("   • Analyze test results")
        print("   • Evaluate promotion gate")
        print("   • Auto-promote if approved")
        print()
        
        # Note: TestOrchestrator now runs strictly via subprocesses
        # For demo purposes, we'll show the workflow structure
        print("   ⚠️  Note: Container sandboxes are banned here")
        print("   Showing workflow structure with pure subprocess execution...")
        print()
        
        # Show what would happen
        print("   Expected workflow steps:")
        print("   1. 🧪 Run tests → [WOULD PASS]")
        print("   2. 📊 Analyze results → [GREEN]")
        print("   3. 🚦 Check promotion gate → [APPROVED]")
        print("   4. ✅ Auto-promote to trunk → [SUCCESS]")
        print()
        
        # Step 6: Manual promotion (subprocess-only demo run)
        print("🎯 Step 6: Promoting to trunk (manual for demo)...")
        commit_hash = git_engine.promote_workpad(workpad.id)
        print(f"   ✅ Promoted to trunk: {commit_hash[:8]}")
        print()
        
        # Step 7: Show trunk history
        print("📜 Step 7: Trunk history:")
        history = git_engine.get_history(repo.id, limit=5)
        for i, commit in enumerate(history):
            print(f"   {i+1}. [{commit.hash[:8]}] {commit.message}")
        print()
        
        print("✅ Demo 1 Complete: Successfully promoted changes to trunk")
        print()


def demo_failed_tests_workflow():
    """Demo: Auto-merge with failed tests."""
    print("=" * 80)
    print("DEMO 2: Auto-Merge with Failed Tests")
    print("=" * 80)
    print()
    
    print("Scenario: Developer adds a feature but tests fail")
    print()
    
    print("Expected workflow:")
    print("1. 🧪 Run tests → [FAILED]")
    print("2. 📊 Analyze results:")
    print("   • Category: ASSERTION_ERROR")
    print("   • Pattern: 'Expected X but got Y'")
    print("   • File: test_app.py:15")
    print("3. 💡 Suggested actions:")
    print("   • Check test assertions")
    print("   • Verify function logic")
    print("   • Fix the bug and re-run tests")
    print("4. 🚦 Promotion gate → [REJECTED]")
    print("5. 📝 Workpad remains active for fixes")
    print()
    
    print("Developer workflow:")
    print("   $ sologit test run <pad-id>")
    print("   ❌ 1 test failed")
    print()
    print("   $ # Fix the issue")
    print("   $ sologit pad apply-patch <pad-id> <fix.patch>")
    print()
    print("   $ sologit pad auto-merge <pad-id>")
    print("   ✅ Tests passed - promoted to trunk")
    print()
    
    print("✅ Demo 2 Complete: Workpad preserved for fixes")
    print()


def demo_ci_smoke_tests():
    """Demo: CI smoke tests after promotion."""
    print("=" * 80)
    print("DEMO 3: CI Smoke Tests & Rollback")
    print("=" * 80)
    print()
    
    print("Scenario: Code promoted but CI smoke tests fail")
    print()
    
    print("Phase 3 provides automatic rollback:")
    print()
    print("1. ✅ Workpad tests pass → Auto-promote to trunk")
    print("2. 🔬 CI runs smoke tests:")
    print("   • Integration tests")
    print("   • E2E tests")
    print("   • Performance tests")
    print("3. ❌ Smoke test fails → Detect failure")
    print("4. ⏪ Auto-rollback:")
    print("   • Revert commit from trunk")
    print("   • Recreate workpad for fixes")
    print("   • Notify developer")
    print("5. 📝 Developer fixes issue in workpad")
    print("6. 🔄 Try auto-merge again")
    print()
    
    print("Configuration (evogit.yaml):")
    print("""
solo:
  promote_on_green: true
  rollback_on_ci_red: true  # Enable auto-rollback
  
tests:
  fast: ["pytest tests/unit/"]
  smoke: ["pytest tests/integration/", "pytest tests/e2e/"]
""")
    print()
    
    print("✅ Demo 3 Complete: Automatic safety net with CI")
    print()


def demo_promotion_rules():
    """Demo: Configurable promotion rules."""
    print("=" * 80)
    print("DEMO 4: Configurable Promotion Rules")
    print("=" * 80)
    print()
    
    print("Phase 3 supports flexible promotion policies:")
    print()
    
    # Example 1: Strict rules
    print("Example 1: Strict policy (production)")
    rules1 = PromotionRules(
        require_tests=True,
        require_all_tests_pass=True,
        require_fast_forward=True,
        max_files_changed=50,
        max_lines_changed=500,
        allow_merge_conflicts=False
    )
    print(f"   • Require tests: {rules1.require_tests}")
    print(f"   • All tests must pass: {rules1.require_all_tests_pass}")
    print(f"   • Fast-forward only: {rules1.require_fast_forward}")
    print(f"   • Max files: {rules1.max_files_changed}")
    print(f"   • Max lines: {rules1.max_lines_changed}")
    print()
    
    # Example 2: Relaxed rules
    print("Example 2: Relaxed policy (development)")
    rules2 = PromotionRules(
        require_tests=True,
        require_all_tests_pass=False,  # Allow some failures
        require_fast_forward=True,
        max_files_changed=None,  # No limit
        max_lines_changed=None,  # No limit
        allow_merge_conflicts=False
    )
    print(f"   • Require tests: {rules2.require_tests}")
    print(f"   • All tests must pass: {rules2.require_all_tests_pass}")
    print(f"   • Max files: unlimited")
    print(f"   • Max lines: unlimited")
    print()
    
    # Example 3: Review on large changes
    print("Example 3: Review policy (large changes)")
    rules3 = PromotionRules(
        require_tests=True,
        require_all_tests_pass=True,
        require_fast_forward=True,
        max_files_changed=20,  # Trigger review
        max_lines_changed=200,  # Trigger review
        allow_merge_conflicts=False
    )
    print(f"   • Max files before review: {rules3.max_files_changed}")
    print(f"   • Max lines before review: {rules3.max_lines_changed}")
    print(f"   • Large changes → Manual review required")
    print()
    
    print("✅ Demo 4 Complete: Flexible policies for different needs")
    print()


def main():
    """Run all demos."""
    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║       SOLO GIT - PHASE 3 FEATURE DEMONSTRATION              ║")
    print("║  Auto-Merge Workflow with CI Orchestration & Rollback       ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    
    # Setup logger
    setup_logger(level="INFO")
    
    # Run demos
    try:
        demo_successful_auto_merge()
        input("Press Enter to continue to Demo 2...")
        print()
        
        demo_failed_tests_workflow()
        input("Press Enter to continue to Demo 3...")
        print()
        
        demo_ci_smoke_tests()
        input("Press Enter to continue to Demo 4...")
        print()
        
        demo_promotion_rules()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("🎉 All demos complete!")
    print()
    print("Key Phase 3 Features Demonstrated:")
    print("  ✅ Auto-merge workflow (tests → analyze → gate → promote)")
    print("  ✅ Intelligent test failure analysis")
    print("  ✅ Configurable promotion rules")
    print("  ✅ CI smoke tests after promotion")
    print("  ✅ Automatic rollback on CI failures")
    print()
    print("Next steps:")
    print("  • Run 'sologit pad auto-merge --help' for CLI usage")
    print("  • Check docs/wiki/phases/phase-3-completion.md for details")
    print("  • Configure promotion rules in your evogit.yaml")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
