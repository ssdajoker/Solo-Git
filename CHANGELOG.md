
# Changelog

All notable changes to Solo Git will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-16

### Added - Phase 0: Foundation & Setup

#### Project Infrastructure
- Created complete project directory structure
- Set up Python package with setuptools
- Added comprehensive README with project vision
- Included MIT License
- Created .gitignore for Python and Solo Git specific files
- Added pyproject.toml for modern Python tooling

#### CLI Framework
- Implemented main CLI with Click framework
- Added `evogitctl` command-line entry point
- Created command group structure (repo, pad, test, config)
- Implemented `hello` command for installation verification
- Implemented `version` command with API status display
- Added `--verbose` flag for detailed logging
- Added `--config` option for custom config file paths

#### Configuration Management
- Built comprehensive configuration system with YAML support
- Implemented environment variable overrides
- Created configuration templates and examples
- Added multi-tier model configuration (planning, coding, fast)
- Implemented budget control settings
- Added test configuration structure
- Created workflow settings (auto-merge, rollback)

#### Configuration Commands
- `config init` - Initialize default config file
- `config setup` - Interactive API credential setup
- `config show` - Display current configuration (with secret masking)
- `config test` - Validate config and test API connection
- `config path` - Show config file location
- `config env-template` - Generate .env template

#### API Client
- Implemented Abacus.ai RouteLLM API client
- Added OpenAI-compatible chat interface
- Implemented streaming support for future use
- Added connection testing functionality
- Included error handling and retry logic

#### Logging System
- Created colored console output with log levels
- Implemented file logging support
- Added verbose mode for debugging
- Included context-aware logging
- Suppressed noisy third-party loggers

#### Documentation
- Created comprehensive README
- Added Phase 0 completion document
- Created setup guide for users
- Included troubleshooting section
- Added changelog

#### Development Tools
- Set up pytest for testing
- Configured Black for code formatting
- Added isort for import sorting
- Included mypy for type checking
- Added flake8 for linting

### Technical Details
- Python 3.9+ compatibility
- Click 8.1+ for CLI framework
- PyYAML 6.0+ for configuration
- Requests 2.31+ for HTTP client
- Modular architecture with clear separation of concerns

### Project Structure
```
solo-git/
├── sologit/              # Main package
│   ├── cli/             # Command-line interface
│   ├── config/          # Configuration management
│   ├── api/             # API clients
│   ├── utils/           # Utilities
│   ├── core/            # Core functionality (future)
│   └── engines/         # Engines (future)
├── tests/               # Test suite
├── docs/                # Documentation
└── [project files]      # README, setup.py, etc.
```

### Notes
- Phase 0 focused on foundation and infrastructure
- All systems tested and verified working
- Ready for Phase 1 Git Engine implementation
- Pure cloud architecture via Abacus.ai API

---

## [Unreleased]

### Planned - Phase 1: Core Git Engine
- Repository initialization from zip/git URL
- Workpad creation and management
- Test orchestration foundation
- Basic merge operations

### Planned - Phase 2: AI Integration
- Model routing and selection
- Planning and patch generation
- Cost tracking and budgets
- Pair loop implementation

### Planned - Phase 3: Testing & Auto-Merge
- Sandboxed test execution
- Auto-merge on green tests
- Jenkins integration
- Auto-rollback on failures

### Planned - Phase 4: Polish & Beta
- Desktop UI (Electron/React)
- Advanced CLI features
- Complete documentation
- Beta release

---

[0.1.0]: https://github.com/yourusername/solo-git/releases/tag/v0.1.0

