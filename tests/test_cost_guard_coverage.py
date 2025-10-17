"""
Additional tests for Cost Guard to improve coverage to 95%+.
"""

import pytest
from datetime import datetime, date, timedelta
from pathlib import Path
import tempfile
import shutil
import json

from sologit.orchestration.cost_guard import (
    CostGuard, CostTracker, BudgetConfig, TokenUsage, DailyUsage
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def tracker(temp_storage):
    """Create a cost tracker with temp storage."""
    storage_path = temp_storage / 'usage.json'
    return CostTracker(storage_path)


@pytest.fixture
def budget_config():
    """Create budget configuration."""
    return BudgetConfig(
        daily_usd_cap=10.0,
        alert_threshold=0.8,
        track_by_model=True
    )


@pytest.fixture
def cost_guard(budget_config, tracker):
    """Create cost guard."""
    return CostGuard(budget_config, tracker)


def test_load_history_with_corrupt_file(temp_storage):
    """Test loading history with corrupt JSON file (lines 103-104)."""
    storage_path = temp_storage / 'usage.json'
    
    # Write corrupt JSON
    with open(storage_path, 'w') as f:
        f.write("{ invalid json content")
    
    # Should handle error gracefully
    tracker = CostTracker(storage_path)
    
    # Should still initialize with today's usage
    assert tracker.current_usage is not None
    assert tracker.get_today_cost() == 0.0


def test_save_history_error_handling(temp_storage):
    """Test save history with write error (lines 122-123)."""
    storage_path = temp_storage / 'usage.json'
    tracker = CostTracker(storage_path)
    
    # Make storage path read-only to trigger save error
    storage_path.touch()
    storage_path.chmod(0o444)
    
    try:
        # This should trigger error logging but not crash
        usage = TokenUsage(
            timestamp=datetime.now(),
            model='gpt-4o',
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.005,
            task_type='planning'
        )
        tracker.record_usage(usage)
        
        # Tracker should still work despite save error
        assert tracker.get_today_cost() == 0.005
    finally:
        # Restore permissions for cleanup
        storage_path.chmod(0o644)


def test_record_usage_day_rollover(temp_storage):
    """Test recording usage with day rollover (lines 135-137)."""
    storage_path = temp_storage / 'usage.json'
    tracker = CostTracker(storage_path)
    
    # Set current usage to None to simulate rollover scenario
    tracker.current_usage = None
    
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=0.005,
        task_type='planning'
    )
    
    # Should create new daily usage for today
    tracker.record_usage(usage)
    
    assert tracker.current_usage is not None
    assert tracker.current_usage.date == date.today()
    assert tracker.get_today_cost() == 0.005


def test_get_today_cost_with_no_usage(temp_storage):
    """Test get_today_cost when no usage (line 166)."""
    storage_path = temp_storage / 'usage.json'
    tracker = CostTracker(storage_path)
    
    # Set current_usage to None
    tracker.current_usage = None
    
    cost = tracker.get_today_cost()
    
    assert cost == 0.0


def test_get_today_tokens_with_no_usage(temp_storage):
    """Test get_today_tokens when no usage (line 172)."""
    storage_path = temp_storage / 'usage.json'
    tracker = CostTracker(storage_path)
    
    # Set current_usage to None
    tracker.current_usage = None
    
    tokens = tracker.get_today_tokens()
    
    assert tokens == 0


def test_get_usage_breakdown_with_no_usage(temp_storage):
    """Test get_usage_breakdown when no usage (line 177)."""
    storage_path = temp_storage / 'usage.json'
    tracker = CostTracker(storage_path)
    
    # Set current_usage to None
    tracker.current_usage = None
    
    breakdown = tracker.get_usage_breakdown()
    
    assert breakdown == {}


def test_record_usage_new_model(tracker):
    """Test recording usage for a new model."""
    usage1 = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=0.005,
        task_type='planning'
    )
    
    tracker.record_usage(usage1)
    
    # Record usage for a different model
    usage2 = TokenUsage(
        timestamp=datetime.now(),
        model='claude-3-5-sonnet',
        prompt_tokens=150,
        completion_tokens=75,
        total_tokens=225,
        cost_usd=0.007,
        task_type='planning'
    )
    
    tracker.record_usage(usage2)
    
    breakdown = tracker.get_usage_breakdown()
    
    assert 'gpt-4o' in breakdown['by_model']
    assert 'claude-3-5-sonnet' in breakdown['by_model']


def test_record_usage_new_task_type(tracker):
    """Test recording usage for a new task type."""
    usage1 = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=0.005,
        task_type='planning'
    )
    
    tracker.record_usage(usage1)
    
    # Record usage for a different task type
    usage2 = TokenUsage(
        timestamp=datetime.now(),
        model='deepseek-coder-33b',
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        cost_usd=0.0015,
        task_type='coding'
    )
    
    tracker.record_usage(usage2)
    
    breakdown = tracker.get_usage_breakdown()
    
    assert 'planning' in breakdown['by_task']
    assert 'coding' in breakdown['by_task']


def test_daily_usage_from_dict_with_missing_fields():
    """Test DailyUsage.from_dict with missing optional fields."""
    data = {
        'date': '2025-10-17',
        'total_cost_usd': 5.0,
        'total_tokens': 10000,
        'calls_count': 10
        # Missing usage_by_model and usage_by_task
    }
    
    usage = DailyUsage.from_dict(data)
    
    assert usage.date == date(2025, 10, 17)
    assert usage.total_cost_usd == 5.0
    assert usage.usage_by_model == {}
    assert usage.usage_by_task == {}


def test_weekly_stats_multiple_days(temp_storage):
    """Test weekly stats with data from multiple days."""
    storage_path = temp_storage / 'usage.json'
    
    # Create tracker and add history for multiple days
    tracker = CostTracker(storage_path)
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Add usage for yesterday
    tracker.usage_history[yesterday] = DailyUsage(
        date=yesterday,
        total_cost_usd=2.0,
        total_tokens=4000,
        calls_count=5
    )
    
    # Add usage for today
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=500,
        completion_tokens=250,
        total_tokens=750,
        cost_usd=1.5,
        task_type='planning'
    )
    tracker.record_usage(usage)
    
    stats = tracker.get_weekly_stats()
    
    # Should include both days
    assert stats['total_cost_usd'] >= 3.5
    assert stats['total_tokens'] >= 4750


def test_cost_guard_with_zero_remaining_budget(cost_guard, tracker):
    """Test cost guard behavior when remaining budget is zero."""
    # Use up all budget
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=10000,
        completion_tokens=5000,
        total_tokens=15000,
        cost_usd=10.0,
        task_type='planning'
    )
    tracker.record_usage(usage)
    
    remaining = cost_guard.get_remaining_budget()
    
    # Should be 0 or negative
    assert remaining <= 0.0
    
    # Should not allow any more usage
    assert cost_guard.check_budget(0.01) is False


def test_budget_alert_not_triggered_below_threshold(cost_guard, tracker, caplog):
    """Test alert is not triggered when below threshold."""
    import logging
    caplog.set_level(logging.WARNING)
    
    # Use 50% of budget (below 80% threshold)
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=5000,
        completion_tokens=2500,
        total_tokens=7500,
        cost_usd=5.0,
        task_type='planning'
    )
    tracker.record_usage(usage)
    
    # Check budget for more usage (should be OK, no alert)
    cost_guard.check_budget(1.0)
    
    # Should not have alert in logs (only at 80%+)
    alert_logs = [r for r in caplog.records if 'alert' in r.message.lower()]
    # Might still have the initialization log, but not budget alert
    assert len([r for r in alert_logs if 'approaching' in r.message.lower()]) == 0
