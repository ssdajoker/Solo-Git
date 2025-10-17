
"""
Cost Guard for budget tracking and enforcement.

Monitors AI API costs and enforces daily budget caps.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional
import json
from pathlib import Path

from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BudgetConfig:
    """Budget configuration."""
    daily_usd_cap: float = 10.0
    alert_threshold: float = 0.8  # Alert at 80%
    track_by_model: bool = True


@dataclass
class TokenUsage:
    """Token usage for a single API call."""
    timestamp: datetime
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    task_type: str  # 'planning', 'coding', 'review', etc.


@dataclass
class DailyUsage:
    """Daily usage statistics."""
    date: date
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    calls_count: int = 0
    usage_by_model: Dict[str, float] = field(default_factory=dict)
    usage_by_task: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'date': self.date.isoformat(),
            'total_cost_usd': self.total_cost_usd,
            'total_tokens': self.total_tokens,
            'calls_count': self.calls_count,
            'usage_by_model': self.usage_by_model,
            'usage_by_task': self.usage_by_task
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DailyUsage':
        """Create from dictionary."""
        return cls(
            date=date.fromisoformat(data['date']),
            total_cost_usd=data['total_cost_usd'],
            total_tokens=data['total_tokens'],
            calls_count=data['calls_count'],
            usage_by_model=data.get('usage_by_model', {}),
            usage_by_task=data.get('usage_by_task', {})
        )


class CostTracker:
    """
    Tracks AI API costs and usage statistics.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize cost tracker.
        
        Args:
            storage_path: Path to store usage data
        """
        self.storage_path = storage_path or Path.home() / '.sologit' / 'usage.json'
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.usage_history: Dict[date, DailyUsage] = {}
        self.current_usage: Optional[DailyUsage] = None
        
        self._load_history()
    
    def _load_history(self):
        """Load usage history from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for entry in data.get('history', []):
                        daily = DailyUsage.from_dict(entry)
                        self.usage_history[daily.date] = daily
                logger.info("Loaded usage history: %d days", len(self.usage_history))
            except Exception as e:
                logger.error("Failed to load usage history: %s", e)
        
        # Initialize current day
        today = date.today()
        if today not in self.usage_history:
            self.usage_history[today] = DailyUsage(date=today)
        self.current_usage = self.usage_history[today]
    
    def _save_history(self):
        """Save usage history to disk."""
        try:
            data = {
                'history': [usage.to_dict() for usage in self.usage_history.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved usage history")
        except Exception as e:
            logger.error("Failed to save usage history: %s", e)
    
    def record_usage(self, usage: TokenUsage):
        """
        Record a token usage event.
        
        Args:
            usage: Token usage details
        """
        # Check if we need to roll over to a new day
        today = date.today()
        if self.current_usage is None or self.current_usage.date != today:
            if today not in self.usage_history:
                self.usage_history[today] = DailyUsage(date=today)
            self.current_usage = self.usage_history[today]
        
        # Update current usage
        self.current_usage.total_cost_usd += usage.cost_usd
        self.current_usage.total_tokens += usage.total_tokens
        self.current_usage.calls_count += 1
        
        # Track by model
        if usage.model not in self.current_usage.usage_by_model:
            self.current_usage.usage_by_model[usage.model] = 0.0
        self.current_usage.usage_by_model[usage.model] += usage.cost_usd
        
        # Track by task type
        if usage.task_type not in self.current_usage.usage_by_task:
            self.current_usage.usage_by_task[usage.task_type] = 0.0
        self.current_usage.usage_by_task[usage.task_type] += usage.cost_usd
        
        logger.debug(
            "Recorded usage: %s, %d tokens, $%.4f",
            usage.model, usage.total_tokens, usage.cost_usd
        )
        
        # Save to disk
        self._save_history()
    
    def get_today_cost(self) -> float:
        """Get today's total cost."""
        if self.current_usage:
            return self.current_usage.total_cost_usd
        return 0.0
    
    def get_today_tokens(self) -> int:
        """Get today's total token count."""
        if self.current_usage:
            return self.current_usage.total_tokens
        return 0
    
    def get_usage_breakdown(self) -> Dict:
        """Get detailed usage breakdown for today."""
        if not self.current_usage:
            return {}
        
        return {
            'date': self.current_usage.date.isoformat(),
            'total_cost_usd': self.current_usage.total_cost_usd,
            'total_tokens': self.current_usage.total_tokens,
            'calls_count': self.current_usage.calls_count,
            'by_model': self.current_usage.usage_by_model,
            'by_task': self.current_usage.usage_by_task
        }
    
    def get_weekly_stats(self) -> Dict:
        """Get weekly usage statistics."""
        from datetime import timedelta
        
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        weekly_cost = 0.0
        weekly_tokens = 0
        weekly_calls = 0
        
        for day, usage in self.usage_history.items():
            if week_ago <= day <= today:
                weekly_cost += usage.total_cost_usd
                weekly_tokens += usage.total_tokens
                weekly_calls += usage.calls_count
        
        return {
            'period': f'{week_ago.isoformat()} to {today.isoformat()}',
            'total_cost_usd': weekly_cost,
            'total_tokens': weekly_tokens,
            'total_calls': weekly_calls,
            'average_daily_cost': weekly_cost / 7.0
        }


class CostGuard:
    """
    Enforces budget constraints and monitors AI costs.
    """
    
    def __init__(self, config: BudgetConfig, tracker: Optional[CostTracker] = None):
        """
        Initialize cost guard.
        
        Args:
            config: Budget configuration
            tracker: Cost tracker (creates new one if None)
        """
        self.config = config
        self.tracker = tracker or CostTracker()
        
        logger.info(
            "CostGuard initialized: $%.2f daily cap, %.0f%% alert threshold",
            config.daily_usd_cap,
            config.alert_threshold * 100
        )
    
    def check_budget(self, estimated_cost: float = 0.0) -> bool:
        """
        Check if a request would exceed the budget.
        
        Args:
            estimated_cost: Estimated cost of the request
        
        Returns:
            True if request is within budget, False otherwise
        """
        current_cost = self.tracker.get_today_cost()
        projected_cost = current_cost + estimated_cost
        
        if projected_cost > self.config.daily_usd_cap:
            logger.warning(
                "Budget exceeded: $%.2f current + $%.2f estimated > $%.2f cap",
                current_cost, estimated_cost, self.config.daily_usd_cap
            )
            return False
        
        # Check if we should alert
        threshold_cost = self.config.daily_usd_cap * self.config.alert_threshold
        if current_cost < threshold_cost <= projected_cost:
            logger.warning(
                "Budget alert: approaching daily cap (%.0f%%)",
                (projected_cost / self.config.daily_usd_cap) * 100
            )
        
        return True
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget for today."""
        current_cost = self.tracker.get_today_cost()
        return max(0.0, self.config.daily_usd_cap - current_cost)
    
    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_per_1k: float,
        task_type: str = "unknown"
    ):
        """
        Record API usage.
        
        Args:
            model: Model name
            prompt_tokens: Prompt token count
            completion_tokens: Completion token count
            cost_per_1k: Cost per 1000 tokens
            task_type: Type of task
        """
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = (total_tokens / 1000.0) * cost_per_1k
        
        usage = TokenUsage(
            timestamp=datetime.now(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            task_type=task_type
        )
        
        self.tracker.record_usage(usage)
    
    def get_status(self) -> Dict:
        """Get current budget status."""
        current_cost = self.tracker.get_today_cost()
        remaining = self.get_remaining_budget()
        percentage_used = (current_cost / self.config.daily_usd_cap) * 100
        
        return {
            'daily_cap': self.config.daily_usd_cap,
            'current_cost': current_cost,
            'remaining': remaining,
            'percentage_used': percentage_used,
            'within_budget': current_cost <= self.config.daily_usd_cap,
            'usage_breakdown': self.tracker.get_usage_breakdown()
        }

