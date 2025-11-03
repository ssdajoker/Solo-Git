"""Tests for telemetry system."""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from sologit.orchestration.telemetry import (
    TelemetryCollector,
    TelemetryEvent,
)
from sologit.orchestration.providers import ProviderType


class TestTelemetryEvent:
    """Test telemetry event dataclass."""
    
    def test_event_creation(self):
        """Test creating a telemetry event."""
        event = TelemetryEvent(
            timestamp=datetime.now(),
            task_type="commit_message",
            provider=ProviderType.ABACUS,
            model="gpt-4o",
            latency_ms=250.0,
            cost_usd=0.001,
            tokens_used=50,
            fallback_used=False,
            success=True,
        )
        
        assert event.task_type == "commit_message"
        assert event.provider == ProviderType.ABACUS
        assert event.model == "gpt-4o"
        assert event.latency_ms == 250.0
        assert event.cost_usd == 0.001
        assert event.tokens_used == 50
        assert event.fallback_used is False
        assert event.success is True


class TestTelemetryCollector:
    """Test telemetry collector."""
    
    def test_collector_initialization(self):
        """Test collector initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            assert collector.telemetry_file == telemetry_file
            assert collector.telemetry_file.parent.exists()
    
    def test_collector_default_path(self):
        """Test collector uses default path when none provided."""
        collector = TelemetryCollector()
        
        assert collector.telemetry_file.parent == Path.home() / ".sologit"
        assert collector.telemetry_file.name == "telemetry.jsonl"
    
    def test_record_event(self):
        """Test recording a single event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            event = TelemetryEvent(
                timestamp=datetime.now(),
                task_type="commit_message",
                provider=ProviderType.ABACUS,
                model="gpt-4o",
                latency_ms=200.0,
                cost_usd=0.001,
                tokens_used=50,
                fallback_used=False,
                success=True,
            )
            
            collector.record_event(event)
            
            # Verify file was created and contains data
            assert telemetry_file.exists()
            
            with open(telemetry_file) as f:
                line = f.readline()
                data = json.loads(line)
                
                assert data["task_type"] == "commit_message"
                assert data["provider"] == "abacus"
                assert data["model"] == "gpt-4o"
                assert data["latency_ms"] == 200.0
                assert data["cost_usd"] == 0.001
                assert data["tokens_used"] == 50
                assert data["fallback_used"] is False
                assert data["success"] is True
    
    def test_record_multiple_events(self):
        """Test recording multiple events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            events = [
                TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.ABACUS,
                    model="gpt-4o",
                    latency_ms=200.0,
                    cost_usd=0.001,
                    tokens_used=50,
                    fallback_used=False,
                    success=True,
                ),
                TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.OPENAI,
                    model="gpt-4o-mini",
                    latency_ms=150.0,
                    cost_usd=0.0005,
                    tokens_used=40,
                    fallback_used=True,
                    success=True,
                ),
            ]
            
            for event in events:
                collector.record_event(event)
            
            # Verify both events were recorded
            with open(telemetry_file) as f:
                lines = f.readlines()
                assert len(lines) == 2
    
    def test_get_summary_empty(self):
        """Test getting summary when no events exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            summary = collector.get_summary(days=30)
            
            assert summary["total_events"] == 0
    
    def test_get_summary_single_event(self):
        """Test getting summary with single event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            event = TelemetryEvent(
                timestamp=datetime.now(),
                task_type="commit_message",
                provider=ProviderType.ABACUS,
                model="gpt-4o",
                latency_ms=200.0,
                cost_usd=0.001,
                tokens_used=50,
                fallback_used=False,
                success=True,
            )
            
            collector.record_event(event)
            summary = collector.get_summary(days=30)
            
            assert summary["total_events"] == 1
            assert summary["total_cost_usd"] == 0.001
            assert summary["avg_latency_ms"] == 200.0
            assert summary["fallback_rate"] == 0.0
            assert summary["success_rate"] == 1.0
            assert summary["provider_usage"]["abacus"] == 1
    
    def test_get_summary_multiple_events(self):
        """Test getting summary with multiple events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            events = [
                TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.ABACUS,
                    model="gpt-4o",
                    latency_ms=200.0,
                    cost_usd=0.001,
                    tokens_used=50,
                    fallback_used=False,
                    success=True,
                ),
                TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.OPENAI,
                    model="gpt-4o-mini",
                    latency_ms=150.0,
                    cost_usd=0.0005,
                    tokens_used=40,
                    fallback_used=True,
                    success=True,
                ),
                TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.ABACUS,
                    model="gpt-4o",
                    latency_ms=180.0,
                    cost_usd=0.0008,
                    tokens_used=45,
                    fallback_used=False,
                    success=True,
                ),
            ]
            
            for event in events:
                collector.record_event(event)
            
            summary = collector.get_summary(days=30)
            
            assert summary["total_events"] == 3
            assert summary["total_cost_usd"] == pytest.approx(0.0023)
            assert summary["avg_latency_ms"] == pytest.approx(176.67, rel=1e-2)
            assert summary["fallback_rate"] == pytest.approx(0.333, rel=1e-2)
            assert summary["success_rate"] == 1.0
            assert summary["provider_usage"]["abacus"] == 2
            assert summary["provider_usage"]["openai"] == 1
    
    def test_get_summary_with_failed_events(self):
        """Test summary calculation with failed events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            events = [
                TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.ABACUS,
                    model="gpt-4o",
                    latency_ms=200.0,
                    cost_usd=0.001,
                    tokens_used=50,
                    fallback_used=False,
                    success=True,
                ),
                TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.OPENAI,
                    model="gpt-4o-mini",
                    latency_ms=150.0,
                    cost_usd=0.0,
                    tokens_used=0,
                    fallback_used=True,
                    success=False,
                ),
            ]
            
            for event in events:
                collector.record_event(event)
            
            summary = collector.get_summary(days=30)
            
            assert summary["total_events"] == 2
            assert summary["success_rate"] == 0.5
    
    def test_get_summary_filters_by_date(self):
        """Test summary filters events by date range."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            # Event from 45 days ago (should be excluded)
            old_event = TelemetryEvent(
                timestamp=datetime.now() - timedelta(days=45),
                task_type="commit_message",
                provider=ProviderType.ABACUS,
                model="gpt-4o",
                latency_ms=200.0,
                cost_usd=0.001,
                tokens_used=50,
                fallback_used=False,
                success=True,
            )
            
            # Event from 10 days ago (should be included)
            recent_event = TelemetryEvent(
                timestamp=datetime.now() - timedelta(days=10),
                task_type="commit_message",
                provider=ProviderType.OPENAI,
                model="gpt-4o-mini",
                latency_ms=150.0,
                cost_usd=0.0005,
                tokens_used=40,
                fallback_used=True,
                success=True,
            )
            
            collector.record_event(old_event)
            collector.record_event(recent_event)
            
            summary = collector.get_summary(days=30)
            
            # Should only include recent event
            assert summary["total_events"] == 1
            assert summary["provider_usage"]["openai"] == 1
            assert "abacus" not in summary["provider_usage"]
    
    def test_get_summary_handles_malformed_data(self):
        """Test summary handles malformed JSON lines gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            # Write some malformed data
            with open(telemetry_file, "w") as f:
                f.write("invalid json\n")
                f.write('{"incomplete": "data"}\n')
            
            # Add valid event
            event = TelemetryEvent(
                timestamp=datetime.now(),
                task_type="commit_message",
                provider=ProviderType.ABACUS,
                model="gpt-4o",
                latency_ms=200.0,
                cost_usd=0.001,
                tokens_used=50,
                fallback_used=False,
                success=True,
            )
            collector.record_event(event)
            
            # Should only count valid event
            summary = collector.get_summary(days=30)
            assert summary["total_events"] == 1
    
    def test_get_summary_calculates_provider_percentages(self):
        """Test provider usage percentages are calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telemetry_file = Path(tmpdir) / "test_telemetry.jsonl"
            collector = TelemetryCollector(telemetry_file)
            
            # Add 7 Abacus events, 2 OpenAI, 1 Anthropic = 10 total
            for i in range(7):
                collector.record_event(TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.ABACUS,
                    model="gpt-4o",
                    latency_ms=200.0,
                    cost_usd=0.001,
                    tokens_used=50,
                    fallback_used=False,
                    success=True,
                ))
            
            for i in range(2):
                collector.record_event(TelemetryEvent(
                    timestamp=datetime.now(),
                    task_type="commit_message",
                    provider=ProviderType.OPENAI,
                    model="gpt-4o-mini",
                    latency_ms=150.0,
                    cost_usd=0.0005,
                    tokens_used=40,
                    fallback_used=True,
                    success=True,
                ))
            
            collector.record_event(TelemetryEvent(
                timestamp=datetime.now(),
                task_type="commit_message",
                provider=ProviderType.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                latency_ms=180.0,
                cost_usd=0.002,
                tokens_used=60,
                fallback_used=True,
                success=True,
            ))
            
            summary = collector.get_summary(days=30)
            
            assert summary["total_events"] == 10
            assert summary["provider_usage"]["abacus"] == 7
            assert summary["provider_usage"]["openai"] == 2
            assert summary["provider_usage"]["anthropic"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
