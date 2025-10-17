"""
Additional tests for Model Router to improve coverage to 90%+.
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


@pytest.fixture
def empty_models_config():
    """Config with empty coding models."""
    return {
        'ai': {
            'models': {
                'fast': {
                    'primary': 'llama-3.1-8b-instruct',
                    'max_tokens': 1024,
                    'temperature': 0.1
                },
                # No coding models configured
                # No planning models configured
            }
        },
        'escalation': {}
    }


def test_model_config_str_representation():
    """Test ModelConfig __str__ method (line 37)."""
    model = ModelConfig(
        name='gpt-4o',
        tier=ModelTier.PLANNING,
        max_tokens=4096,
        temperature=0.2,
        cost_per_1k_tokens=0.03
    )
    
    result = str(model)
    
    assert 'gpt-4o' in result
    assert 'planning' in result


def test_complexity_metrics_str_representation():
    """Test ComplexityMetrics __str__ method (line 51)."""
    metrics = ComplexityMetrics(
        score=0.75,
        security_sensitive=True,
        estimated_patch_size=150,
        file_count=3,
        has_tests=True,
        requires_architecture=False
    )
    
    result = str(metrics)
    
    assert '0.75' in result
    assert 'security=true' in result.lower()  # Fixed: lowercase comparison
    assert '150' in result


def test_complexity_score_large_patch_branches(router):
    """Test complexity score calculation for large patches (lines 245-248)."""
    # Test line 245-246: elif estimated_patch_size < 200
    complexity1 = router.analyze_complexity(
        prompt=" ".join(["implement"] * 40),  # ~160 chars, triggers line 245-246
        context=None
    )
    # Patch size should be between 100 and 200
    assert complexity1.estimated_patch_size >= 100
    assert complexity1.score > 0
    
    # Test line 248: else (>= 200)
    complexity2 = router.analyze_complexity(
        prompt=" ".join(["refactor"] * 60),  # Triggers refactor multiplier and large size
        context=None
    )
    # Patch size calculation: len(prompt.split()) * 2 * 2.0 = 60 * 2 * 2.0 = 240
    assert complexity2.estimated_patch_size >= 200


def test_select_tier_architecture_task(router):
    """Test tier selection for architecture tasks (lines 319-321)."""
    complexity = ComplexityMetrics(
        score=0.5,
        security_sensitive=False,
        estimated_patch_size=100,
        file_count=2,
        has_tests=True,
        requires_architecture=True  # This triggers line 319-321
    )
    
    tier = router._select_tier(complexity, 100.0)
    
    assert tier == ModelTier.PLANNING


def test_select_tier_large_patch(router):
    """Test tier selection for large patches (lines 323-325)."""
    complexity = ComplexityMetrics(
        score=0.5,
        security_sensitive=False,
        estimated_patch_size=250,  # Triggers line 323-325
        file_count=2,
        has_tests=True,
        requires_architecture=False
    )
    
    tier = router._select_tier(complexity, 100.0)
    
    assert tier == ModelTier.PLANNING


def test_select_tier_medium_complexity(router):
    """Test tier selection for medium complexity (lines 328-331)."""
    # Test line 329: score >= 0.7
    complexity1 = ComplexityMetrics(
        score=0.75,
        security_sensitive=False,
        estimated_patch_size=100,
        file_count=2,
        has_tests=True,
        requires_architecture=False
    )
    
    tier1 = router._select_tier(complexity1, 100.0)
    assert tier1 == ModelTier.PLANNING
    
    # Test line 331: score >= 0.3
    complexity2 = ComplexityMetrics(
        score=0.4,
        security_sensitive=False,
        estimated_patch_size=100,
        file_count=2,
        has_tests=True,
        requires_architecture=False
    )
    
    tier2 = router._select_tier(complexity2, 100.0)
    assert tier2 == ModelTier.CODING


def test_get_model_for_tier_no_models(empty_models_config):
    """Test getting model when tier has no models (lines 352-354)."""
    router = ModelRouter(empty_models_config)
    
    # Try to get a model for CODING tier (which has no models)
    model = router._get_model_for_tier(ModelTier.CODING, 100.0)
    
    # Should fall back to FAST tier
    assert model.tier == ModelTier.FAST


def test_escalate_from_coding_tier(router):
    """Test escalation from CODING tier (line 385-386)."""
    coding_model = router.models[ModelTier.CODING][0]
    
    escalated = router.get_escalated_model(coding_model, reason="failure")
    
    assert escalated is not None
    assert escalated.tier == ModelTier.PLANNING


def test_escalate_from_planning_tier_returns_none(router):
    """Test escalation from PLANNING tier returns None (line 388-389)."""
    planning_model = router.models[ModelTier.PLANNING][0]
    
    escalated = router.get_escalated_model(planning_model, reason="failure")
    
    # Already at highest tier, should return None
    assert escalated is None


def test_complexity_with_multiple_files_in_prompt(router):
    """Test complexity detection for multiple files mentioned."""
    complexity = router.analyze_complexity(
        prompt="update multiple files in the authentication module",
        context={'file_count': 1}
    )
    
    # Should detect "multiple files" and increase file count
    assert complexity.file_count >= 3


def test_complexity_with_test_mention(router):
    """Test has_tests flag detection."""
    complexity1 = router.analyze_complexity(
        prompt="add feature with comprehensive test coverage",
        context=None
    )
    
    assert complexity1.has_tests is True
    
    complexity2 = router.analyze_complexity(
        prompt="add feature with spec files",
        context=None
    )
    
    assert complexity2.has_tests is True


def test_estimate_patch_size_with_keywords(router):
    """Test patch size estimation with various keywords."""
    # Test "add" keyword (1.5x multiplier)
    size_add = router._estimate_patch_size("add new feature", {})
    
    # Test "refactor" keyword (2.0x multiplier)
    size_refactor = router._estimate_patch_size("refactor the codebase", {})
    
    # Test "simple" keyword (0.5x multiplier)
    size_simple = router._estimate_patch_size("simple quick fix", {})
    
    # Refactor should estimate more lines than add
    assert size_refactor > size_add
    
    # Simple should estimate fewer lines
    assert size_simple < size_add


def test_get_model_for_tier_with_low_budget(router):
    """Test model selection with low budget uses cheaper models."""
    # With low budget and multiple models, should pick cheaper
    model = router._get_model_for_tier(ModelTier.PLANNING, budget_remaining=0.5)
    
    # Should return a model (might be cheaper fallback if available)
    assert model is not None
    assert model.tier == ModelTier.PLANNING
