# Tilt MCP Server

A Model Context Protocol (MCP) server that integrates with [Tilt](https://tilt.dev/) to provide programmatic access to Tilt resources and logs through LLM applications.

## Overview

The Tilt MCP server allows Large Language Models (LLMs) and AI assistants to interact with your Tilt development environment. It provides tools to:

- List all enabled Tilt resources
- Fetch logs from specific resources
- Monitor resource status and health
- Enable and disable resources dynamically
- Get detailed information about resources
- Trigger resource rebuilds
- Wait for resources to reach specific conditions

This enables AI-powered development workflows, debugging assistance, automated monitoring, and intelligent resource management of your Tilt-managed services.

## Available MCP Tools

The Tilt MCP server exposes the following tools to MCP clients:

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_all_resources` | Lists all enabled Tilt resources with their status | None |
| `get_resource_logs` | Fetches logs from a specific resource | `resource_name` (required), `tail` (optional, default: 1000) |
| `trigger_resource` | Triggers a Tilt resource to rebuild/update | `resource_name` (required) |
| `enable_resource` | Enables one or more Tilt resources | `resource_names` (required, list), `enable_only` (optional, default: false) |
| `disable_resource` | Disables one or more Tilt resources | `resource_names` (required, list) |
| `describe_resource` | Get detailed information about a specific resource | `resource_name` (required) |
| `wait_for_resource` | Wait for a resource to reach a specific condition | `resource_name` (required), `condition` (optional, default: 'Ready'), `timeout_seconds` (optional, default: 30) |

### Tool Details

All tools return structured JSON responses and include comprehensive error handling:
- **Resource Not Found**: Raises `ValueError` with helpful message
- **Tilt Connection Issues**: Raises `RuntimeError` with Tilt error details
- **JSON Parsing Errors**: Provides detailed parsing error information

All tool executions are logged to `~/.tilt-mcp/tilt_mcp.log` for debugging.

## Features

- 🔍 **Resource Discovery**: List all active Tilt resources with their current status
- 📜 **Log Retrieval**: Fetch recent logs from any Tilt resource
- 🔄 **Resource Triggering**: Manually trigger Tilt resources to rebuild/update
- ✅ **Resource Control**: Enable or disable resources dynamically
- 📋 **Detailed Information**: Get comprehensive details about any resource
- ⏳ **Wait Conditions**: Wait for resources to reach specific states
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
        "${HOME}/.tilt-dev:/tmp/host-tilt-dev:ro",
        "-v",
        "${HOME}/.tilt-mcp:/home/mcp-user/.tilt-mcp",
        "--network=host",
        "ghcr.io/rrmistry/tilt-mcp:latest"
      ],
      "env": {}
    }
  }
}
```

**For Windows (PowerShell):**
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
        "${env:USERPROFILE}\\.tilt-dev:/tmp/host-tilt-dev:ro",
        "-v",
        "${env:USERPROFILE}\\.tilt-mcp:/home/mcp-user/.tilt-mcp",
        "--network=host",
        "ghcr.io/rrmistry/tilt-mcp:latest"
      ],
      "env": {}
    }
  }
}
```

**For Windows (CMD):**
Use `%USERPROFILE%` instead of `${env:USERPROFILE}` in the volume mount paths.

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

### `trigger_resource`

Triggers a Tilt resource to rebuild/update. This is useful for manually triggering resources that have `trigger_mode: manual` or for forcing a rebuild.

Parameters:
- `resource_name` (string, required): Name of the Tilt resource to trigger

Example request:
```json
{
  "resource_name": "backend"
}
```

Example response:
```json
{
  "success": true,
  "resource": "backend",
  "message": "Resource \"backend\" has been triggered",
  "output": ""
}
```

### `enable_resource`

Enables one or more Tilt resources. Can optionally enable specific resources while disabling all others.

Parameters:
- `resource_names` (list of strings, required): Names of the Tilt resources to enable
- `enable_only` (boolean, optional): If true, enables these resources and disables all others (default: false)

Example request:
```json
{
  "resource_names": ["frontend", "backend"],
  "enable_only": false
}
```

Example response:
```json
{
  "success": true,
  "resources": ["frontend", "backend"],
  "enable_only": false,
  "message": "Resources ['frontend', 'backend'] have been enabled",
  "output": ""
}
```

### `disable_resource`

Disables one or more Tilt resources. Useful for temporarily stopping resources without tearing down the entire Tilt environment.

Parameters:
- `resource_names` (list of strings, required): Names of the Tilt resources to disable

Example request:
```json
{
  "resource_names": ["frontend", "backend"]
}
```

Example response:
```json
{
  "success": true,
  "resources": ["frontend", "backend"],
  "message": "Resources ['frontend', 'backend'] have been disabled",
  "output": ""
}
```

### `describe_resource`

Gets detailed information about a specific Tilt resource, including its configuration, status, build history, and runtime information.

Parameters:
- `resource_name` (string, required): Name of the Tilt resource to describe

Example request:
```json
{
  "resource_name": "frontend"
}
```

Example response:
```
Name:         frontend
Namespace:
Labels:       type=k8s
Annotations:  <none>
API Version:  tilt.dev/v1alpha1
Kind:         UIResource
...
(detailed resource information)
```

### `wait_for_resource`

Waits for a Tilt resource to reach a specific condition. This is particularly useful for automation and ensuring resources are ready before proceeding with other operations.

Parameters:
- `resource_name` (string, required): Name of the Tilt resource to wait for
- `condition` (string, optional): The condition to wait for (default: "Ready"). Common conditions include "Ready", "Updated"
- `timeout_seconds` (integer, optional): Maximum time to wait in seconds (default: 30)

Example request:
```json
{
  "resource_name": "backend",
  "condition": "Ready",
  "timeout_seconds": 60
}
```

Example response:
```json
{
  "success": true,
  "resource": "backend",
  "condition": "Ready",
  "message": "Resource \"backend\" reached condition \"Ready\"",
  "output": "uiresource.tilt.dev/backend condition met"
}
```

## Example Prompts

Here are some example prompts you can use with an AI assistant that has access to this MCP server:

**Resource Discovery & Status:**
- "Show me all the Tilt resources that are currently running"
- "Which services are failing or have errors?"
- "Compare the status of frontend and backend services"
- "Give me detailed information about the backend resource"

**Log Analysis:**
- "Get the last 100 lines of logs from the backend-api service"
- "Show me the recent logs from all services that aren't healthy"
- "Show me error logs from any failing services"
- "Help me debug why the frontend service is crashing"

**Resource Control:**
- "Disable the frontend and backend services"
- "Enable only the database service and disable everything else"
- "Enable the frontend service"
- "Disable all non-essential services to save resources"

**Build & Deployment:**
- "Trigger a rebuild of the backend service"
- "Rebuild the frontend and show me the logs"
- "Trigger all services that have errors"
- "Wait for the backend to be ready before checking its logs"

**Automation Workflows:**
- "Enable the backend, wait for it to be ready, then check its logs"
- "Disable all services, then enable only frontend and wait for it to start"
- "Describe the database resource and show me its recent logs"
- "Trigger a rebuild of the API service and wait until it's ready"

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
