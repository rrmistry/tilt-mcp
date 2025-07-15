# Contributing to Tilt MCP

Thank you for your interest in contributing to Tilt MCP! This guide will help you get started with contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Documentation](#documentation)

## Code of Conduct

This project follows a standard code of conduct. Please be respectful and considerate in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up your development environment
4. Make your changes
5. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Tilt installed and working
- Git

### Setting up your environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/tilt-mcp.git
cd tilt-mcp

# Add upstream remote
git remote add upstream https://github.com/aryan-agrawal-glean/tilt-mcp.git

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

## Making Changes

### Creating a branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
```

### Development workflow

1. Make your changes
2. Add or update tests as needed
3. Update documentation if necessary
4. Run tests and linting
5. Commit your changes

### Running the server locally

```bash
# Run the server directly
python -m tilt_mcp.server

# Or use MCP CLI
mcp run python -m tilt_mcp.server
```

## Testing

### Running tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tilt_mcp

# Run specific test file
pytest tests/test_server.py

# Run with verbose output
pytest -v
```

### Writing tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test names
- Mock external dependencies (especially Tilt commands)

Example test structure:

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_get_all_resources():
    """Test that get_all_resources returns correct data"""
    # Your test code here
    pass
```

## Submitting Changes

### Code quality checks

Before submitting, ensure your code passes all checks:

```bash
# Format code
black src tests

# Run linter
ruff check src tests

# Type checking
mypy src

# Run all tests
pytest
```

### Commit messages

Follow conventional commit format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `style:` Code style changes
- `chore:` Maintenance tasks

Examples:
```
feat: add support for filtering resources by status
fix: handle empty log responses correctly
docs: update installation instructions for Windows
```

### Pull Request Process

1. Update your branch with latest main:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

3. Create a Pull Request on GitHub

4. Fill out the PR template with:
   - Description of changes
   - Related issue numbers
   - Testing performed
   - Screenshots (if UI changes)

5. Wait for review and address feedback

## Code Style

### Python Style Guide

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use type hints for all functions
- Add docstrings to all public functions and classes

### Example:

```python
from typing import List, Dict, Optional

async def get_resource_info(
    resource_name: str, 
    include_logs: bool = False
) -> Dict[str, any]:
    """
    Get detailed information about a Tilt resource.
    
    Args:
        resource_name: Name of the Tilt resource
        include_logs: Whether to include recent logs
        
    Returns:
        Dictionary containing resource information
        
    Raises:
        ValueError: If resource not found
    """
    # Implementation here
    pass
```

## Documentation

### Updating Documentation

- Update README.md for user-facing changes
- Update inline docstrings for API changes
- Add examples for new features
- Update CHANGELOG.md

### Documentation Standards

- Use clear, concise language
- Include code examples
- Explain both the "what" and "why"
- Keep formatting consistent

## Release Process

Releases are managed by maintainers. The process is:

1. Update version in `pyproject.toml` and `src/tilt_mcp/__init__.py`
2. Update CHANGELOG.md
3. Create a git tag
4. Build and publish to PyPI

## Getting Help

If you need help:

1. Check existing issues and discussions
2. Ask in the project discussions
3. Open an issue with your question

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- GitHub contributors page

Thank you for contributing to Tilt MCP! 