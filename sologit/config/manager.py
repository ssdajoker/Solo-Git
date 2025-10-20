
"""
Configuration management for Solo Git.

Handles loading, saving, and validating configuration from YAML files
and environment variables. Supports API credentials, model settings,
budget controls, and test configurations.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AbacusAPIConfig:
    """Abacus.ai API configuration."""
    endpoint: str = "https://api.abacus.ai/v1"
    api_key: Optional[str] = None
    
    def is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.api_key)


@dataclass
class ModelConfig:
    """Model configuration for different task types."""
    # Planning models (GPT-4, Claude, Llama 70B)
    planning_model: str = "gpt-4o"
    planning_fallback: str = "claude-3-5-sonnet"
    planning_max_tokens: int = 4096
    planning_temperature: float = 0.2
    
    # Coding models (DeepSeek, CodeLlama)
    coding_model: str = "deepseek-coder-33b"
    coding_fallback: str = "codellama-70b-instruct"
    coding_max_tokens: int = 2048
    coding_temperature: float = 0.1
    
    # Fast operation models (Llama 8B, Gemma)
    fast_model: str = "llama-3.1-8b-instruct"
    fast_fallback: str = "gemma-2-9b-it"
    fast_max_tokens: int = 1024
    fast_temperature: float = 0.1


@dataclass
class BudgetConfig:
    """Budget and cost control configuration."""
    daily_usd_cap: float = 10.0
    alert_threshold: float = 0.8
    track_by_model: bool = True
    escalation_triggers: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.escalation_triggers is None:
            self.escalation_triggers = {
                "patch_lines": 200,
                "test_failures": 2,
                "security_keywords": ["auth", "crypto", "password", "token", "jwt"],
                "complexity_score": 0.7
            }


@dataclass
class TestConfig:
    """Test execution configuration."""
    sandbox_image: str = "ghcr.io/solo-git/sandbox:latest"
    timeout_seconds: int = 300
    parallel_max: int = 4
    fast_tests: list = None
    full_tests: list = None
    execution_mode: str = "auto"
    log_dir: Optional[str] = None

    def __post_init__(self):
        if self.fast_tests is None:
            self.fast_tests = []
        if self.full_tests is None:
            self.full_tests = []
        if self.log_dir is None:
            self.log_dir = str(Path.home() / ".sologit" / "data" / "test_runs")


@dataclass
class SoloGitConfig:
    """Main Solo Git configuration."""
    # Repository settings
    repos_path: str = "~/.sologit/repos"
    workpad_ttl_days: int = 7
    
    # Solo workflow settings
    promote_on_green: bool = True
    rollback_on_ci_red: bool = True
    
    # Component configs
    abacus: AbacusAPIConfig = None
    models: ModelConfig = None
    budget: BudgetConfig = None
    tests: TestConfig = None
    
    def __post_init__(self):
        if self.abacus is None:
            self.abacus = AbacusAPIConfig()
        if self.models is None:
            self.models = ModelConfig()
        if self.budget is None:
            self.budget = BudgetConfig()
        if self.tests is None:
            self.tests = TestConfig()
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary format."""
        return {
            'repos_path': self.repos_path,
            'workpad_ttl_days': self.workpad_ttl_days,
            'promote_on_green': self.promote_on_green,
            'rollback_on_ci_red': self.rollback_on_ci_red,
            'abacus': {
                'endpoint': self.abacus.endpoint,
                'api_key': self.abacus.api_key
            },
            'ai': {
                'models': {
                    'fast': {
                        'primary': self.models.fast_model,
                        'max_tokens': 1024,
                        'temperature': 0.1
                    },
                    'coding': {
                        'primary': self.models.coding_model,
                        'max_tokens': 2048,
                        'temperature': 0.1
                    },
                    'planning': {
                        'primary': self.models.planning_model,
                        'max_tokens': 4096,
                        'temperature': 0.2
                    }
                }
            },
            'escalation': {
                'triggers': []
            },
            'budget': {
                'daily_usd_cap': self.budget.daily_usd_cap,
                'alert_threshold': self.budget.alert_threshold,
                'track_by_model': self.budget.track_by_model
            },
            'tests': {
                'sandbox_image': self.tests.sandbox_image,
                'timeout_seconds': self.tests.timeout_seconds,
                'parallel_max': self.tests.parallel_max,
                'execution_mode': self.tests.execution_mode,
                'log_dir': self.tests.log_dir,
            }
        }


class ConfigManager:
    """Manages Solo Git configuration."""
    
    DEFAULT_CONFIG_DIR = Path.home() / ".sologit"
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Optional path to config file. If None, uses default location.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_FILE
        self.config = self._load_config()
    
    def _load_config(self) -> SoloGitConfig:
        """
        Load configuration from file and environment variables.
        
        Priority (highest to lowest):
        1. Environment variables
        2. Config file
        3. Defaults
        """
        # Start with defaults
        config = SoloGitConfig()
        
        # Load from file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config = self._merge_config(config, file_config)
                        logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
        else:
            logger.debug(f"No config file found at {self.config_path}, using defaults")
        
        # Override with environment variables
        config = self._load_env_overrides(config)
        
        return config
    
    def _merge_config(self, base: SoloGitConfig, override: Dict) -> SoloGitConfig:
        """Merge configuration from dict into base config."""
        # Abacus API
        if 'abacus' in override:
            if 'endpoint' in override['abacus']:
                base.abacus.endpoint = override['abacus']['endpoint']
            if 'api_key' in override['abacus']:
                base.abacus.api_key = override['abacus']['api_key']
        
        # Models
        if 'models' in override:
            for key, value in override['models'].items():
                if hasattr(base.models, key):
                    setattr(base.models, key, value)
        
        # Budget
        if 'budget' in override:
            for key, value in override['budget'].items():
                if hasattr(base.budget, key):
                    setattr(base.budget, key, value)
        
        # Tests
        if 'tests' in override:
            for key, value in override['tests'].items():
                if hasattr(base.tests, key):
                    setattr(base.tests, key, value)
        
        # Top-level settings
        if 'repos_path' in override:
            base.repos_path = override['repos_path']
        if 'workpad_ttl_days' in override:
            base.workpad_ttl_days = override['workpad_ttl_days']
        if 'promote_on_green' in override:
            base.promote_on_green = override['promote_on_green']
        if 'rollback_on_ci_red' in override:
            base.rollback_on_ci_red = override['rollback_on_ci_red']
        
        return base
    
    def _load_env_overrides(self, config: SoloGitConfig) -> SoloGitConfig:
        """Load configuration overrides from environment variables."""
        # Abacus API
        if os.getenv('ABACUS_API_ENDPOINT'):
            config.abacus.endpoint = os.getenv('ABACUS_API_ENDPOINT')
        if os.getenv('ABACUS_API_KEY'):
            config.abacus.api_key = os.getenv('ABACUS_API_KEY')
        
        # Budget
        if os.getenv('DAILY_USD_CAP'):
            config.budget.daily_usd_cap = float(os.getenv('DAILY_USD_CAP'))
        
        # Repos path
        if os.getenv('SOLOGIT_REPOS_PATH'):
            config.repos_path = os.getenv('SOLOGIT_REPOS_PATH')
        
        return config
    
    def save_config(self):
        """Save current configuration to file."""
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict
        config_dict = {
            'abacus': {
                'endpoint': self.config.abacus.endpoint,
                'api_key': self.config.abacus.api_key
            },
            'models': asdict(self.config.models),
            'budget': asdict(self.config.budget),
            'tests': {
                'sandbox_image': self.config.tests.sandbox_image,
                'timeout_seconds': self.config.tests.timeout_seconds,
                'parallel_max': self.config.tests.parallel_max,
                'fast_tests': self.config.tests.fast_tests,
                'full_tests': self.config.tests.full_tests
            },
            'repos_path': self.config.repos_path,
            'workpad_ttl_days': self.config.workpad_ttl_days,
            'promote_on_green': self.config.promote_on_green,
            'rollback_on_ci_red': self.config.rollback_on_ci_red
        }
        
        # Write to file
        with open(self.config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration saved to {self.config_path}")
    
    def has_abacus_credentials(self) -> bool:
        """Check if Abacus.ai API credentials are configured."""
        return self.config.abacus.is_configured()
    
    def get_config(self) -> SoloGitConfig:
        """Get the current configuration."""
        return self.config
    
    def set_abacus_credentials(self, api_key: str, endpoint: Optional[str] = None):
        """Set Abacus.ai API credentials."""
        self.config.abacus.api_key = api_key
        if endpoint:
            self.config.abacus.endpoint = endpoint
        self.save_config()
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the current configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check API credentials
        if not self.config.abacus.is_configured():
            errors.append("Abacus.ai API key not configured")
        
        # Validate budget
        if self.config.budget.daily_usd_cap <= 0:
            errors.append("Daily USD cap must be positive")
        
        if not 0 < self.config.budget.alert_threshold <= 1:
            errors.append("Alert threshold must be between 0 and 1")
        
        # Validate test settings
        if self.config.tests.timeout_seconds <= 0:
            errors.append("Test timeout must be positive")
        
        if self.config.tests.parallel_max <= 0:
            errors.append("Parallel max must be positive")
        
        return len(errors) == 0, errors

