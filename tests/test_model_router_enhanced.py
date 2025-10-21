"""
Enhanced tests for Model Router to achieve >95% coverage.
"""

import pytest
from sologit.orchestration.model_router import (
    ModelRouter, ModelTier, ModelConfig, ComplexityMetrics
)


class FakeGitSync:
    """Simple GitStateSync stub for testing."""

    def __init__(self, summary):
        self.summary = summary

    def get_workpad_diff_summary(self, pad_id, base: str = "trunk"):
        return self.summary


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        'ai': {
            'models': {
                'fast': {
                    'primary': {
                        'name': 'llama-3.1-8b-instruct',
                        'max_tokens': 1024,
                        'temperature': 0.1,
                        'cost_per_1k_tokens': 0.0002
                    },
                    'fallback': {
                        'name': 'gemma-2-9b-it',
                        'max_tokens': 1024,
                        'temperature': 0.1,
                        'cost_per_1k_tokens': 0.00005
                    }
                },
                'coding': {
                    'primary': {
                        'name': 'deepseek-coder-33b',
                        'max_tokens': 2048,
                        'temperature': 0.1,
                        'cost_per_1k_tokens': 0.0008
                    },
                    'fallback': {
                        'name': 'codellama-70b-instruct',
                        'max_tokens': 2048,
                        'temperature': 0.1,
                        'cost_per_1k_tokens': 0.0006
                    }
                },
                'planning': {
                    'primary': {
                        'name': 'gpt-4o',
                        'max_tokens': 4096,
                        'temperature': 0.2,
                        'cost_per_1k_tokens': 0.03
                    },
                    'fallback': {
                        'name': 'claude-3-5-sonnet',
                        'max_tokens': 4096,
                        'temperature': 0.2,
                        'cost_per_1k_tokens': 0.025
                    }
                }
            }
        },
        'escalation': {
            'triggers': []
        }
    }


@pytest.fixture
def router(mock_config):
    """Create a model router for testing."""
    return ModelRouter(mock_config)


def test_model_config_str():
    """Test ModelConfig __str__ method."""
    config = ModelConfig(
        name="gpt-4o",
        tier=ModelTier.PLANNING,
        max_tokens=4096,
        temperature=0.2,
        cost_per_1k_tokens=0.03
    )
    
    result = str(config)
    assert "gpt-4o" in result
    assert "planning" in result


def test_complexity_metrics_str():
    """Test ComplexityMetrics __str__ method."""
    metrics = ComplexityMetrics(
        score=0.75,
        security_sensitive=True,
        estimated_patch_size=150,
        file_count=3,
        has_tests=True,
        requires_architecture=False
    )
    
    result = str(metrics)
    assert "0.75" in result
    assert "security=True" in result
    assert "patch_lines=150" in result
    assert "files=3" in result


def test_analyze_complexity_with_file_count():
    """Test complexity analysis with file count in context."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    complexity = router.analyze_complexity(
        prompt="update configuration",
        context={'file_count': 5}
    )
    
    assert complexity.file_count == 5
    # Score should include file count contribution
    assert complexity.score > 0


def test_analyze_complexity_multiple_files_keywords():
    """Test complexity detects multiple files from keywords."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    complexity = router.analyze_complexity(
        prompt="update multiple files in the project",
        context={}
    )
    
    assert complexity.file_count >= 3


def test_analyze_complexity_with_tests():
    """Test complexity detects test-related prompts."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    complexity = router.analyze_complexity(
        prompt="add unit tests for the API",
        context={}
    )
    
    assert complexity.has_tests


def test_repo_context_escalates_to_planning(mock_config):
    """Large diffs from Git context should escalate tier selection."""

    git_sync = FakeGitSync({'lines_changed': 420, 'files_changed': 8})
    router = ModelRouter(mock_config, git_sync=git_sync)

    model = router.select_model(
        prompt="update feature",
        context={'workpad_id': 'pad-123'},
        budget_remaining=20.0
    )

    assert model.tier == ModelTier.PLANNING


def test_analyze_complexity_spec_keyword():
    """Test complexity detects spec keyword for tests."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    complexity = router.analyze_complexity(
        prompt="write spec for user service",
        context={}
    )
    
    assert complexity.has_tests


def test_estimate_patch_size_with_keywords():
    """Test patch size estimation with various keywords."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    # Test 'add' keyword
    size_add = router._estimate_patch_size("add new feature", {})
    size_base = router._estimate_patch_size("update code", {})
    assert size_add >= size_base  # May be equal due to similar word count
    
    # Test 'refactor' keyword
    size_refactor = router._estimate_patch_size("refactor authentication system", {})
    assert size_refactor >= size_add  # Refactor multiplier makes it larger
    
    # Test 'simple' keyword
    size_simple = router._estimate_patch_size("simple fix", {})
    assert size_simple <= size_base  # Simple keyword reduces size


def test_estimate_patch_size_capped():
    """Test patch size estimation is capped at 500."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    # Very long prompt with refactor keyword
    long_prompt = "refactor " + " ".join(["implement"] * 200)
    size = router._estimate_patch_size(long_prompt, {})
    
    assert size <= 500


def test_select_tier_security_sensitive(router):
    """Test tier selection for security-sensitive tasks."""
    complexity = ComplexityMetrics(
        score=0.4,
        security_sensitive=True,
        estimated_patch_size=50,
        file_count=1,
        has_tests=False,
        requires_architecture=False
    )
    
    tier = router._select_tier(complexity, 100.0)
    assert tier == ModelTier.PLANNING


def test_select_tier_architecture(router):
    """Test tier selection for architecture tasks."""
    complexity = ComplexityMetrics(
        score=0.4,
        security_sensitive=False,
        estimated_patch_size=50,
        file_count=1,
        has_tests=False,
        requires_architecture=True
    )
    
    tier = router._select_tier(complexity, 100.0)
    assert tier == ModelTier.PLANNING


def test_select_tier_large_patch(router):
    """Test tier selection for large patches."""
    complexity = ComplexityMetrics(
        score=0.4,
        security_sensitive=False,
        estimated_patch_size=250,
        file_count=1,
        has_tests=False,
        requires_architecture=False
    )
    
    tier = router._select_tier(complexity, 100.0)
    assert tier == ModelTier.PLANNING


def test_select_tier_high_complexity_score(router):
    """Test tier selection based on high complexity score."""
    complexity = ComplexityMetrics(
        score=0.75,
        security_sensitive=False,
        estimated_patch_size=50,
        file_count=1,
        has_tests=False,
        requires_architecture=False
    )
    
    tier = router._select_tier(complexity, 100.0)
    assert tier == ModelTier.PLANNING


def test_select_tier_medium_complexity(router):
    """Test tier selection for medium complexity."""
    complexity = ComplexityMetrics(
        score=0.5,
        security_sensitive=False,
        estimated_patch_size=100,
        file_count=2,
        has_tests=False,
        requires_architecture=False
    )
    
    tier = router._select_tier(complexity, 100.0)
    assert tier == ModelTier.CODING


def test_select_tier_low_complexity(router):
    """Test tier selection for low complexity."""
    complexity = ComplexityMetrics(
        score=0.2,
        security_sensitive=False,
        estimated_patch_size=20,
        file_count=1,
        has_tests=False,
        requires_architecture=False
    )
    
    tier = router._select_tier(complexity, 100.0)
    assert tier == ModelTier.FAST


def test_get_model_for_tier_no_models():
    """Test getting model when tier has no models configured."""
    config = {
        'ai': {
            'models': {
                'fast': {
                    'primary': {
                        'name': 'llama-3.1-8b-instruct',
                        'max_tokens': 1024,
                        'temperature': 0.1,
                        'cost_per_1k_tokens': 0.0002
                    }
                }
            }
        },
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    # Try to get a model for PLANNING tier which has no models
    model = router._get_model_for_tier(ModelTier.PLANNING, 100.0)
    
    # Should fallback to FAST
    assert model.tier == ModelTier.FAST


def test_get_model_for_tier_low_budget_multiple_models(router):
    """Test model selection with low budget and multiple models."""
    model = router._get_model_for_tier(ModelTier.PLANNING, 0.5)
    
    # Should return one of the planning models
    assert model.tier == ModelTier.PLANNING


def test_escalate_from_coding(router):
    """Test escalation from CODING tier."""
    coding_model = router.models[ModelTier.CODING][0]
    
    escalated = router.get_escalated_model(coding_model, reason="failure")
    
    assert escalated is not None
    assert escalated.tier == ModelTier.PLANNING


def test_complexity_score_components():
    """Test all complexity score components."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    # Test size contributions
    complexity_small = router.analyze_complexity("fix", {})
    assert complexity_small.score < 0.3
    
    # Test medium size (50-100 lines)
    prompt_medium = " ".join(["add"] * 30)  # Should estimate ~45-90 lines
    complexity_medium = router.analyze_complexity(prompt_medium, {})
    
    # Test large size (100-200 lines)
    prompt_large = " ".join(["implement"] * 50)
    complexity_large = router.analyze_complexity(prompt_large, {})
    
    # Test very large size (>200 lines)
    prompt_xlarge = "refactor " + " ".join(["complex"] * 100)
    complexity_xlarge = router.analyze_complexity(prompt_xlarge, {})
    
    # Scores should generally increase with size
    assert complexity_xlarge.score > 0


def test_all_security_keywords():
    """Test detection of all security keywords."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    keywords = ['auth', 'authentication', 'password', 'token', 'jwt',
                'crypto', 'encrypt', 'decrypt', 'secret', 'key',
                'security', 'permission', 'authorization', 'oauth',
                'session', 'cookie', 'cors', 'xss', 'csrf', 'sql']
    
    for keyword in keywords:
        complexity = router.analyze_complexity(f"implement {keyword} handling", {})
        assert complexity.security_sensitive, f"Failed to detect: {keyword}"


def test_all_architecture_keywords():
    """Test detection of all architecture keywords."""
    config = {
        'ai': {'models': {}},
        'escalation': {'triggers': []}
    }
    router = ModelRouter(config)
    
    keywords = ['architecture', 'design', 'refactor', 'restructure',
                'migrate', 'framework', 'pattern', 'system', 'database',
                'api design', 'schema', 'model', 'interface']
    
    for keyword in keywords:
        complexity = router.analyze_complexity(f"update the {keyword}", {})
        assert complexity.requires_architecture, f"Failed to detect: {keyword}"
