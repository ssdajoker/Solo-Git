"""Configuration management for Solo Git.

Handles loading, saving, and validating configuration from YAML files and
environment variables. Supports API credentials, model settings, budget
controls, deployment credentials, and test configurations.
"""

import base64
import hashlib
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any

import yaml

from sologit.utils.logger import get_logger

logger = get_logger(__name__)

try:  # Optional strong encryption support
    from cryptography.fernet import Fernet, InvalidToken  # type: ignore
except Exception:  # pragma: no cover - cryptography is optional
    Fernet = None  # type: ignore
    InvalidToken = Exception  # type: ignore


@dataclass
class AbacusAPIConfig:
    """Abacus.ai API configuration."""

    endpoint: str = "https://api.abacus.ai/v1"
    api_key: Optional[str] = None

    def is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.api_key)


@dataclass
class DeploymentCredentials:
    """Deployment credentials for Abacus.ai deployments."""

    deployment_id: str
    deployment_token: str
    token_scheme: str = "plain"

    @property
    def has_token(self) -> bool:
        """Return whether a usable token is available."""
        return bool(self.deployment_token)


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
                "complexity_score": 0.7,
            }


@dataclass
class TestConfig:
    """Test execution configuration."""

    sandbox_image: str = "ghcr.io/solo-git/sandbox:latest"
    timeout_seconds: int = 300
    parallel_max: int = 4
    fast_tests: list = None
    full_tests: list = None

    def __post_init__(self):
        if self.fast_tests is None:
            self.fast_tests = []
        if self.full_tests is None:
            self.full_tests = []


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
    deployments: Dict[str, DeploymentCredentials] = None

    def __post_init__(self):
        if self.abacus is None:
            self.abacus = AbacusAPIConfig()
        if self.models is None:
            self.models = ModelConfig()
        if self.budget is None:
            self.budget = BudgetConfig()
        if self.tests is None:
            self.tests = TestConfig()
        if self.deployments is None:
            self.deployments = {}

    def to_dict(self) -> dict:
        """Convert configuration to dictionary format."""
        return {
            'repos_path': self.repos_path,
            'workpad_ttl_days': self.workpad_ttl_days,
            'promote_on_green': self.promote_on_green,
            'rollback_on_ci_red': self.rollback_on_ci_red,
            'abacus': {
                'endpoint': self.abacus.endpoint,
                'api_key': self.abacus.api_key,
            },
            'ai': {
                'models': {
                    'fast': {
                        'primary': self.models.fast_model,
                        'max_tokens': 1024,
                        'temperature': 0.1,
                    },
                    'coding': {
                        'primary': self.models.coding_model,
                        'max_tokens': 2048,
                        'temperature': 0.1,
                    },
                    'planning': {
                        'primary': self.models.planning_model,
                        'max_tokens': 4096,
                        'temperature': 0.2,
                    },
                }
            },
            'escalation': {
                'triggers': []
            },
            'budget': {
                'daily_usd_cap': self.budget.daily_usd_cap,
                'alert_threshold': self.budget.alert_threshold,
                'track_by_model': self.budget.track_by_model,
            },
            'tests': {
                'sandbox_image': self.tests.sandbox_image,
                'timeout_seconds': self.tests.timeout_seconds,
                'parallel_max': self.tests.parallel_max,
            },
            'deployments': {
                name: {
                    'deployment_id': creds.deployment_id,
                    'has_token': creds.has_token,
                }
                for name, creds in self.deployments.items()
            },
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
        self._fernet = self._build_fernet()
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
                        logger.info("Loaded configuration from %s", self.config_path)
            except Exception as e:
                logger.warning("Failed to load config file: %s", e)
        else:
            logger.debug("No config file found at %s, using defaults", self.config_path)

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

        # Deployment credentials
        deployments = override.get('deployments')
        if isinstance(deployments, dict):
            merged: Dict[str, DeploymentCredentials] = {}
            for name, creds in deployments.items():
                if not isinstance(creds, dict):
                    continue
                deployment_id = creds.get('deployment_id', '')
                token_value = creds.get('deployment_token', '')
                scheme = creds.get('token_scheme', 'plain')
                if token_value:
                    try:
                        deployment_token = self._decrypt_secret(token_value, scheme)
                    except Exception as exc:  # pragma: no cover - logging only
                        logger.warning(
                            "Failed to decrypt deployment token for %s: %s", name, exc
                        )
                        deployment_token = ''
                else:
                    deployment_token = ''
                merged[name] = DeploymentCredentials(
                    deployment_id=deployment_id,
                    deployment_token=deployment_token,
                    token_scheme=scheme,
                )
            base.deployments = merged

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
            config.abacus.endpoint = os.getenv('ABACUS_API_ENDPOINT')  # type: ignore[assignment]
        if os.getenv('ABACUS_API_KEY'):
            config.abacus.api_key = os.getenv('ABACUS_API_KEY')

        # Budget
        if os.getenv('DAILY_USD_CAP'):
            config.budget.daily_usd_cap = float(os.getenv('DAILY_USD_CAP'))

        # Repos path
        if os.getenv('SOLOGIT_REPOS_PATH'):
            config.repos_path = os.getenv('SOLOGIT_REPOS_PATH')  # type: ignore[assignment]

        return config

    def save_config(self):
        """Save current configuration to file."""
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        config_dict = {
            'abacus': {
                'endpoint': self.config.abacus.endpoint,
                'api_key': self.config.abacus.api_key,
            },
            'models': asdict(self.config.models),
            'budget': asdict(self.config.budget),
            'tests': {
                'sandbox_image': self.config.tests.sandbox_image,
                'timeout_seconds': self.config.tests.timeout_seconds,
                'parallel_max': self.config.tests.parallel_max,
                'fast_tests': self.config.tests.fast_tests,
                'full_tests': self.config.tests.full_tests,
            },
            'repos_path': self.config.repos_path,
            'workpad_ttl_days': self.config.workpad_ttl_days,
            'promote_on_green': self.config.promote_on_green,
            'rollback_on_ci_red': self.config.rollback_on_ci_red,
            'deployments': {},
        }

        for name, creds in self.config.deployments.items():
            token_value, scheme = self._encrypt_secret(creds.deployment_token)
            config_dict['deployments'][name] = {
                'deployment_id': creds.deployment_id,
                'deployment_token': token_value,
                'token_scheme': scheme,
            }
            creds.token_scheme = scheme

        # Write to file
        with open(self.config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        logger.info("Configuration saved to %s", self.config_path)

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

    def set_deployment_credentials(
        self,
        name: str,
        deployment_id: str,
        deployment_token: str,
    ):
        """Persist deployment credentials for an Abacus.ai deployment."""
        if not self.config.deployments:
            self.config.deployments = {}
        self.config.deployments[name] = DeploymentCredentials(
            deployment_id=deployment_id,
            deployment_token=deployment_token,
        )
        self.save_config()

    def get_deployment_credentials(self, name: str) -> Optional[DeploymentCredentials]:
        """Retrieve deployment credentials by name."""
        return self.config.deployments.get(name)

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

    def _build_fernet(self):
        """Initialise Fernet instance if encryption key is available."""
        secret = os.getenv('SOLOGIT_CONFIG_SECRET')
        if not secret:
            logger.debug(
                "No SOLOGIT_CONFIG_SECRET provided; storing deployment tokens without Fernet encryption"
            )
            return None
        if not Fernet:
            logger.warning(
                "cryptography not installed; unable to use Fernet encryption for deployment tokens"
            )
            return None

        digest = hashlib.sha256(secret.encode('utf-8')).digest()
        key = base64.urlsafe_b64encode(digest)
        try:
            return Fernet(key)
        except Exception as exc:  # pragma: no cover - Fernet rarely fails here
            logger.warning("Failed to initialise Fernet encryption: %s", exc)
            return None

    def _encrypt_secret(self, value: str) -> tuple[str, str]:
        """Encrypt or obfuscate a secret for storage."""
        if not value:
            return "", "plain"

        if self._fernet:
            try:
                return (
                    self._fernet.encrypt(value.encode('utf-8')).decode('utf-8'),
                    'fernet',
                )
            except Exception as exc:  # pragma: no cover - unexpected encryption failure
                logger.error("Failed to encrypt secret with Fernet: %s", exc)

        # Fallback to reversible base64 encoding to avoid cleartext storage
        encoded = base64.urlsafe_b64encode(value.encode('utf-8')).decode('utf-8')
        return encoded, 'base64'

    def _decrypt_secret(self, value: str, scheme: str) -> str:
        """Decode or decrypt a secret retrieved from storage."""
        if not value:
            return ''

        if scheme == 'fernet' and self._fernet:
            try:
                return self._fernet.decrypt(value.encode('utf-8')).decode('utf-8')
            except InvalidToken as exc:
                raise ValueError("Invalid Fernet token for deployment secret") from exc
            except Exception as exc:  # pragma: no cover - unexpected decrypt failure
                raise ValueError(f"Failed to decrypt deployment secret: {exc}") from exc

        if scheme == 'base64':
            try:
                return base64.urlsafe_b64decode(value.encode('utf-8')).decode('utf-8')
            except Exception as exc:
                raise ValueError(f"Failed to decode base64 secret: {exc}") from exc

        # Default to plain storage
        return value
