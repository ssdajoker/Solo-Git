"""
Telemetry for AI provider usage.
Tracks: provider usage, latency, costs, fallback rate.
"""
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from sologit.orchestration.providers import ProviderType


@dataclass
class TelemetryEvent:
    """Single telemetry event."""
    timestamp: datetime
    task_type: str  # "commit_message", "code_generation", etc.
    provider: ProviderType
    model: str
    latency_ms: float
    cost_usd: float
    tokens_used: int
    fallback_used: bool
    success: bool


class TelemetryCollector:
    """Collects and persists telemetry data."""
    
    def __init__(self, telemetry_file: Path = None):
        if telemetry_file is None:
            telemetry_file = Path.home() / ".sologit" / "telemetry.jsonl"
        self.telemetry_file = telemetry_file
        self.telemetry_file.parent.mkdir(parents=True, exist_ok=True)
    
    def record_event(self, event: TelemetryEvent):
        """Record telemetry event."""
        with open(self.telemetry_file, "a") as f:
            f.write(json.dumps({
                "timestamp": event.timestamp.isoformat(),
                "task_type": event.task_type,
                "provider": event.provider.value,
                "model": event.model,
                "latency_ms": event.latency_ms,
                "cost_usd": event.cost_usd,
                "tokens_used": event.tokens_used,
                "fallback_used": event.fallback_used,
                "success": event.success,
            }) + "\n")
    
    def get_summary(self, days: int = 30) -> dict:
        """Get telemetry summary for last N days."""
        events = []
        cutoff = datetime.now().timestamp() - (days * 86400)
        
        if not self.telemetry_file.exists():
            return {"total_events": 0}
        
        with open(self.telemetry_file) as f:
            for line in f:
                try:
                    event = json.loads(line)
                    ts = datetime.fromisoformat(event["timestamp"]).timestamp()
                    if ts >= cutoff:
                        events.append(event)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        if not events:
            return {"total_events": 0}
        
        # Aggregate stats
        total_cost = sum(e["cost_usd"] for e in events)
        total_latency = sum(e["latency_ms"] for e in events)
        provider_counts = {}
        fallback_count = sum(1 for e in events if e["fallback_used"])
        success_count = sum(1 for e in events if e["success"])
        
        for event in events:
            provider = event["provider"]
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        return {
            "total_events": len(events),
            "total_cost_usd": total_cost,
            "avg_latency_ms": total_latency / len(events),
            "provider_usage": provider_counts,
            "fallback_rate": fallback_count / len(events),
            "success_rate": success_count / len(events),
        }
