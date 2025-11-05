# Solo Git API Reference

This document provides a comprehensive reference for the Solo Git command-line interface (CLI) and its underlying Python API.

---

## 1. CLI Command Reference

The `evogitctl` command is the primary entry point for all Solo Git operations.

### Global Options

| Option | Description |
|---|---|
| `-v, --verbose` | Enable verbose logging. |
| `--config PATH` | Use a custom configuration file. |
| `--help` | Show help for any command. |

### Core Commands

- **`evogitctl config`**: Manage configuration.
  - `setup`: Interactive configuration wizard.
  - `show`: Display the current configuration.
  - `test`: Test the API connection.
- **`evogitctl repo`**: Manage repositories.
  - `init`: Initialize a new repository from a zip file or Git URL.
  - `list`: List all repositories.
  - `info`: Show detailed information about a repository.
- **`evogitctl pad`**: Manage workpads.
  - `create <title>`: Create a new workpad.
  - `list`: List all active workpads.
  - `info <pad-id>`: Show detailed information about a workpad.
  - `promote <pad-id>`: Promote a workpad to the trunk.
  - `delete <pad-id>`: Delete a workpad.
- **`evogitctl test`**: Run tests.
  - `run`: Run tests in a sandboxed environment.
  - `config`: Show the test configuration.
  - `analyze`: Analyze test failures with AI.
- **`evogitctl pair`**: AI-assisted development.
  - `pair "<prompt>"`: The main AI pair programming loop.

---

## 2. Python API Reference

The Python API provides programmatic access to Solo Git's core functionality.

### Key Modules

- **`sologit.engines.git_engine`**: Core Git operations, including repository and workpad management.
- **`sologit.orchestration.ai_orchestrator`**: The main entry point for AI-powered development workflows.
- **`sologit.workflows.auto_merge`**: The complete, automated workflow for testing and promoting changes.

For detailed information on the Python API, including class and method signatures, please refer to the docstrings within the source code.

---

This API reference provides a high-level overview of the Solo Git CLI and Python API. For more detailed information, please use the `--help` flag on any CLI command or refer to the source code.
