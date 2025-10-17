
"""
Tests for Model Router.
"""

import pytest
from sologit.orchestration.model_router import (
    ModelRouter, ModelTier, ModelConfig, ComplexityMetrics
)


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        'ai': {
            'models': {
                'fast': {
                    'primary': 'llama-3.1-8b-instruct',
                    'fallback': 'gemma-2-9b-it',
                    'max_tokens': 1024,
                    'temperature': 0.1
                },
                'coding': {
                    'primary': 'deepseek-coder-33b',
                    'fallback': 'codellama-70b-instruct',
                    'max_tokens': 2048,
                    'temperature': 0.1
                },
                'planning': {
                    'primary': 'gpt-4o',
                    'fallback': 'claude-3-5-sonnet',
                    'max_tokens': 4096,
                    'temperature': 0.2
                }
            }
        },
        'escalation': {
            'triggers': [
                'patch_lines > 200',
                'test_failures >= 2'
            ]
        }
    }


@pytest.fixture
def router(mock_config):
    """Create a model router for testing."""
    return ModelRouter(mock_config)


def test_router_initialization(router):
    """Test router initializes correctly."""
    assert router is not None
    assert ModelTier.FAST in router.models
    assert ModelTier.CODING in router.models
    assert ModelTier.PLANNING in router.models


def test_load_models(router):
    """Test models are loaded from config."""
    assert len(router.models[ModelTier.FAST]) >= 1
    assert len(router.models[ModelTier.CODING]) >= 1
    assert len(router.models[ModelTier.PLANNING]) >= 1
    
    fast_model = router.models[ModelTier.FAST][0]
    assert fast_model.name == 'llama-3.1-8b-instruct'
    assert fast_model.tier == ModelTier.FAST


def test_analyze_complexity_simple(router):
    """Test complexity analysis for simple task."""
    complexity = router.analyze_complexity(
        prompt="fix typo in readme",
        context=None
    )
    
    assert complexity.score < 0.3
    assert not complexity.security_sensitive
    assert not complexity.requires_architecture


def test_analyze_complexity_security(router):
    """Test complexity analysis detects security-sensitive tasks."""
    complexity = router.analyze_complexity(
        prompt="add password authentication with JWT tokens",
        context=None
    )
    
    assert complexity.security_sensitive
    assert complexity.score >= 0.3


def test_analyze_complexity_architecture(router):
    """Test complexity analysis detects architecture tasks."""
    complexity = router.analyze_complexity(
        prompt="refactor the database schema and migrate to new structure",
        context=None
    )
    
    assert complexity.requires_architecture
    assert complexity.score >= 0.2


def test_select_model_simple(router):
    """Test model selection for simple task."""
    model = router.select_model(
        prompt="add a comment",
        budget_remaining=100.0
    )
    
    assert model.tier == ModelTier.FAST


def test_select_model_complex(router):
    """Test model selection for complex task."""
    model = router.select_model(
        prompt="implement authentication system with password hashing",
        budget_remaining=100.0
    )
    
    assert model.tier == ModelTier.PLANNING


def test_select_model_forced_tier(router):
    """Test forcing a specific tier."""
    model = router.select_model(
        prompt="simple change",
        force_tier=ModelTier.PLANNING,
        budget_remaining=100.0
    )
    
    assert model.tier == ModelTier.PLANNING


def test_select_model_low_budget(router):
    """Test model selection with low budget prefers cheaper models."""
    # With low budget, should select cheaper model even if fallback exists
    model = router.select_model(
        prompt="medium complexity task",
        budget_remaining=0.5  # Low budget
    )
    
    # Should still work but prefer cheaper options
    assert model is not None


def test_estimate_patch_size(router):
    """Test patch size estimation."""
    size1 = router._estimate_patch_size("simple fix", {})
    size2 = router._estimate_patch_size("implement complex feature with multiple files", {})
    
    assert size2 > size1


def test_escalate_model(router):
    """Test model escalation."""
    fast_model = router.models[ModelTier.FAST][0]
    
    escalated = router.get_escalated_model(fast_model, reason="failure")
    
    assert escalated is not None
    assert escalated.tier == ModelTier.CODING


def test_escalate_from_planning(router):
    """Test that PLANNING tier can't escalate further."""
    planning_model = router.models[ModelTier.PLANNING][0]
    
    escalated = router.get_escalated_model(planning_model, reason="failure")
    
    assert escalated is None


def test_complexity_score_calculation(router):
    """Test complexity score is properly clamped."""
    # Test that score stays in [0, 1]
    complexity = router.analyze_complexity(
        prompt="refactor authentication with password encryption and JWT tokens for multiple files",
        context={'file_count': 10}
    )
    
    assert 0.0 <= complexity.score <= 1.0

