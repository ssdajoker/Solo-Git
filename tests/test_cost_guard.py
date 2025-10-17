
"""
Tests for Cost Guard and Budget Tracking.
"""

import pytest
from datetime import datetime, date
from pathlib import Path
import tempfile
import shutil

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


def test_tracker_initialization(tracker):
    """Test tracker initializes correctly."""
    assert tracker is not None
    assert tracker.current_usage is not None
    assert tracker.current_usage.date == date.today()


def test_record_usage(tracker):
    """Test recording token usage."""
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
    
    assert tracker.get_today_cost() == 0.005
    assert tracker.get_today_tokens() == 150
    assert tracker.current_usage.calls_count == 1


def test_record_multiple_usage(tracker):
    """Test recording multiple usage events."""
    for i in range(3):
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
    
    assert tracker.get_today_cost() == 0.015
    assert tracker.get_today_tokens() == 450
    assert tracker.current_usage.calls_count == 3


def test_track_by_model(tracker):
    """Test tracking costs by model."""
    usage1 = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=0.005,
        task_type='planning'
    )
    
    usage2 = TokenUsage(
        timestamp=datetime.now(),
        model='deepseek-coder-33b',
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        cost_usd=0.0015,
        task_type='coding'
    )
    
    tracker.record_usage(usage1)
    tracker.record_usage(usage2)
    
    breakdown = tracker.get_usage_breakdown()
    
    assert 'gpt-4o' in breakdown['by_model']
    assert 'deepseek-coder-33b' in breakdown['by_model']
    assert breakdown['by_model']['gpt-4o'] == 0.005
    assert breakdown['by_model']['deepseek-coder-33b'] == 0.0015


def test_track_by_task(tracker):
    """Test tracking costs by task type."""
    usage1 = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=0.005,
        task_type='planning'
    )
    
    usage2 = TokenUsage(
        timestamp=datetime.now(),
        model='deepseek-coder-33b',
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        cost_usd=0.0015,
        task_type='coding'
    )
    
    tracker.record_usage(usage1)
    tracker.record_usage(usage2)
    
    breakdown = tracker.get_usage_breakdown()
    
    assert 'planning' in breakdown['by_task']
    assert 'coding' in breakdown['by_task']
    assert breakdown['by_task']['planning'] == 0.005
    assert breakdown['by_task']['coding'] == 0.0015


def test_persistence(temp_storage):
    """Test usage data is persisted."""
    storage_path = temp_storage / 'usage.json'
    
    # Create tracker and record usage
    tracker1 = CostTracker(storage_path)
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=0.005,
        task_type='planning'
    )
    tracker1.record_usage(usage)
    
    # Create new tracker with same storage
    tracker2 = CostTracker(storage_path)
    
    # Should load previous data
    assert tracker2.get_today_cost() == 0.005


def test_check_budget_within_limit(cost_guard):
    """Test budget check when within limit."""
    # No usage yet, should be within budget
    assert cost_guard.check_budget(5.0) is True


def test_check_budget_exceeds_limit(cost_guard, tracker):
    """Test budget check when exceeding limit."""
    # Record usage close to cap
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=10000,
        completion_tokens=5000,
        total_tokens=15000,
        cost_usd=9.5,
        task_type='planning'
    )
    tracker.record_usage(usage)
    
    # Try to use more than remaining budget
    assert cost_guard.check_budget(1.0) is False


def test_budget_alert_threshold(cost_guard, tracker, caplog):
    """Test alert is triggered at threshold."""
    import logging
    caplog.set_level(logging.WARNING)
    
    # Use 70% of budget
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=7000,
        completion_tokens=3500,
        total_tokens=10500,
        cost_usd=7.0,
        task_type='planning'
    )
    tracker.record_usage(usage)
    
    # This should trigger alert (crossing 80% threshold)
    cost_guard.check_budget(2.0)
    
    assert any('alert' in record.message.lower() for record in caplog.records)


def test_get_remaining_budget(cost_guard, tracker):
    """Test getting remaining budget."""
    assert cost_guard.get_remaining_budget() == 10.0
    
    # Record some usage
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cost_usd=3.0,
        task_type='planning'
    )
    tracker.record_usage(usage)
    
    assert cost_guard.get_remaining_budget() == 7.0


def test_record_usage_through_guard(cost_guard):
    """Test recording usage through cost guard."""
    cost_guard.record_usage(
        model='gpt-4o',
        prompt_tokens=100,
        completion_tokens=50,
        cost_per_1k=0.03,
        task_type='planning'
    )
    
    # Cost should be (150 / 1000) * 0.03 = 0.0045
    assert abs(cost_guard.tracker.get_today_cost() - 0.0045) < 0.0001


def test_get_status(cost_guard, tracker):
    """Test getting budget status."""
    usage = TokenUsage(
        timestamp=datetime.now(),
        model='gpt-4o',
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cost_usd=3.0,
        task_type='planning'
    )
    tracker.record_usage(usage)
    
    status = cost_guard.get_status()
    
    assert status['daily_cap'] == 10.0
    assert status['current_cost'] == 3.0
    assert status['remaining'] == 7.0
    assert status['percentage_used'] == 30.0
    assert status['within_budget'] is True


def test_daily_usage_serialization():
    """Test DailyUsage serialization."""
    usage = DailyUsage(
        date=date(2025, 10, 17),
        total_cost_usd=5.0,
        total_tokens=10000,
        calls_count=10,
        usage_by_model={'gpt-4o': 5.0},
        usage_by_task={'planning': 5.0}
    )
    
    # Convert to dict
    data = usage.to_dict()
    
    assert data['date'] == '2025-10-17'
    assert data['total_cost_usd'] == 5.0
    
    # Convert back
    restored = DailyUsage.from_dict(data)
    
    assert restored.date == date(2025, 10, 17)
    assert restored.total_cost_usd == 5.0


def test_weekly_stats(tracker):
    """Test getting weekly statistics."""
    # Record some usage
    for i in range(3):
        usage = TokenUsage(
            timestamp=datetime.now(),
            model='gpt-4o',
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=1.0,
            task_type='planning'
        )
        tracker.record_usage(usage)
    
    stats = tracker.get_weekly_stats()
    
    assert 'total_cost_usd' in stats
    assert 'total_tokens' in stats
    assert 'average_daily_cost' in stats
    assert stats['total_cost_usd'] == 3.0

