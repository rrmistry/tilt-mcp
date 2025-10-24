# Tilt MCP Server

A Model Context Protocol (MCP) server that integrates with [Tilt](https://tilt.dev/) to provide programmatic access to Tilt resources and logs through LLM applications.

## Overview

The Tilt MCP server allows Large Language Models (LLMs) and AI assistants to interact with your Tilt development environment. It provides tools to:

- List all enabled Tilt resources
- Fetch logs from specific resources
- Monitor resource status and health

This enables AI-powered development workflows, debugging assistance, and automated monitoring of your Tilt-managed services.

## Available MCP Tools

The Tilt MCP server exposes the following tools to MCP clients:

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_all_resources` | Lists all enabled Tilt resources with their status | None |
| `get_resource_logs` | Fetches logs from a specific resource | `resource_name` (required), `tail` (optional, default: 1000) |

### Tool Details

Both tools return structured JSON responses and include comprehensive error handling:
- **Resource Not Found**: Raises `ValueError` with helpful message
- **Tilt Connection Issues**: Raises `RuntimeError` with Tilt error details
- **JSON Parsing Errors**: Provides detailed parsing error information

All tool executions are logged to `~/.tilt-mcp/tilt_mcp.log` for debugging.

## Features

- 🔍 **Resource Discovery**: List all active Tilt resources with their current status
- 📜 **Log Retrieval**: Fetch recent logs from any Tilt resource
- 🛡️ **Type Safety**: Built with Python type hints for better IDE support
- 🚀 **Async Support**: Fully asynchronous implementation using FastMCP
- 📊 **Structured Output**: Returns well-formatted JSON responses

## Prerequisites

- Python 3.8 or higher
- [Tilt](https://docs.tilt.dev/install.html) installed and configured
- An MCP-compatible client (e.g., Claude Desktop, mcp-cli)

## Installation

You can install Tilt MCP in three ways:

### Option 1: Using Docker (Recommended for macOS/Windows)

The Docker-based installation requires no Python setup and is automatically kept up-to-date with monthly builds.

See the [MCP Configuration](#configuration) section below for setup instructions.

### Option 2: From PyPI

```bash
pip install tilt-mcp
```

**Best for:** Linux users or when you prefer local installation

### Option 3: From Source

```bash
git clone https://github.com/rrmistry/tilt-mcp.git
cd tilt-mcp
pip install -e .
```

**Best for:** Development or testing local changes

## Configuration

### Docker Configuration (Recommended for macOS/Windows)

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/claude/claude_desktop_config.json`

**For macOS/Linux:**
```json
{
  "mcpServers": {
    "tilt": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "${HOME}/.tilt-dev:/home/mcp-user/.tilt-dev",
        "--network=host",
        "ghcr.io/rrmistry/tilt-mcp:latest"
      ],
      "env": {}
    }
  }
}
```

**For Windows:**

Similar to the macOS/Linux configuration, but replace `${HOME}` with `%USERPROFILE%` for CMD or `${USERPROFILE}` for PowerShell for the volume mount for `~/.tilt-dev`.

### Local Installation Configuration

If you installed via PyPI or from source, use this simpler configuration:

```json
{
  "mcpServers": {
    "tilt": {
      "command": "tilt-mcp"
    }
  }
}
```

Making sure that `tilt-mcp` is in your PATH.

### For Development/Testing

You can run the server directly:

```bash
python -m tilt_mcp.server
```

Or use it with the MCP CLI:

```bash
mcp run python -m tilt_mcp.server
```

### Checking Version

To check the installed version of tilt-mcp:

```bash
tilt-mcp --version
```

## Usage

Once configured, the Tilt MCP server provides the following tools:

### `get_all_resources`

Lists all enabled Tilt resources with their current status.

Example response:
```json
[
  {
    "name": "frontend",
    "type": "k8s",
    "status": "ok",
    "updateStatus": "ok"
  },
  {
    "name": "backend-api",
    "type": "k8s", 
    "status": "pending",
    "updateStatus": "pending"
  }
]
```

### `get_resource_logs`

Fetches recent logs from a specific Tilt resource.

Parameters:
- `resource_name` (string, required): Name of the Tilt resource
- `tail` (integer, optional): Number of log lines to return (default: 1000)

Example request:
```json
{
  "resource_name": "frontend",
  "tail": 50
}
```

Example response:
```json
{
  "logs": "2024-01-15 10:23:45 INFO Starting server on port 3000\n2024-01-15 10:23:46 INFO Server ready"
}
```

## Example Prompts

Here are some example prompts you can use with an AI assistant that has access to this MCP server:

- "Show me all the Tilt resources that are currently running"
- "Get the last 100 lines of logs from the backend-api service"
- "Which services are failing or have errors?"
- "Show me the recent logs from all services that aren't healthy"
- "Help me debug why the frontend service is crashing"
- "Compare the status of frontend and backend services"
- "Show me error logs from any failing services"

## Development

### Setting up the development environment

```bash
# Clone the repository
git clone https://github.com/yourusername/tilt-mcp.git
cd tilt-mcp

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running tests

```bash
pytest
```

### Code formatting and linting

```bash
# Format code
black src tests

# Run linter
ruff check src tests

# Type checking
mypy src
```

## Troubleshooting

### Common Issues

1. **"Tilt not found" error**
   - Ensure Tilt is installed and available in your PATH
   - Try running `tilt version` to verify installation

2. **"No resources found" when Tilt is running**
   - Make sure your Tiltfile is loaded and resources are started
   - Check that you're running the MCP server in the correct directory

3. **Connection errors**
   - Verify the MCP client configuration is correct
   - Check the logs at `~/.tilt-mcp/tilt_mcp.log`

4. **Docker based tilt-mcp not able to connect**
    - There is a known issue with tilt https://github.com/tilt-dev/tilt/issues/6612 that prevents docker based tilt-mcp from connecting to the Tilt API server.
    - A workaround is to mount the `~/.tilt-dev` directory in the container.
    - Check if your local tilt instance is creating this directory and where it is located.

### Debug Logging

The MCP server logs all operations to `~/.tilt-mcp/tilt_mcp.log`. The log includes:
- Server startup/shutdown events
- Resource fetch operations
- Log retrieval operations
- Error messages with full details

To enable debug logging, set the environment variable:

```bash
export LOG_LEVEL=DEBUG
```

**Log Format**: `timestamp - logger_name - level - message`

**Viewing Logs**:
```bash
# View recent logs
tail -f ~/.tilt-mcp/tilt_mcp.log

# Search for errors
grep ERROR ~/.tilt-mcp/tilt_mcp.log

# View logs from a specific resource fetch
grep "get_all_resources" ~/.tilt-mcp/tilt_mcp.log
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up your development environment
- Running tests
- Submitting pull requests
- Code style guidelines

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) for the MCP server implementation
- Integrates with [Tilt](https://tilt.dev/) for Kubernetes development

## Support

- 📧 Email: aryan.agrawal@glean.com
- 💬 Issues: [GitHub Issues](https://github.com/rrmistry/tilt-mcp/issues)
