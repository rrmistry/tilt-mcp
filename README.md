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

## Available MCP Capabilities

The Tilt MCP server follows the Model Context Protocol specification and exposes three types of capabilities:

### 🔍 Resources (Read-Only Data)

Resources provide read-only access to Tilt data. They're automatically discovered by MCP clients and can be accessed via their URI.

| Resource URI | Description |
|--------------|-------------|
| `tilt://resources/all` | List of all enabled Tilt resources with their current status |
| `tilt://resources/{resource_name}/logs` | Logs from a specific resource (supports `?tail=N` query parameter) |
| `tilt://resources/{resource_name}/describe` | Detailed information about a specific resource |

**Example URIs:**
- `tilt://resources/all` - Get all resources
- `tilt://resources/frontend/logs?tail=100` - Get last 100 lines from frontend
- `tilt://resources/backend/describe` - Get detailed info about backend

### 🛠️ Tools (Actions with Side Effects)

Tools enable LLMs to perform actions that modify the state of your Tilt environment.

| Tool | Description | Parameters |
|------|-------------|------------|
| `trigger_resource` | Triggers a Tilt resource to rebuild/update | `resource_name` (required) |
| `enable_resource` | Enables one or more Tilt resources | `resource_names` (required, list), `enable_only` (optional, default: false) |
| `disable_resource` | Disables one or more Tilt resources | `resource_names` (required, list) |
| `wait_for_resource` | Wait for a resource to reach a specific condition | `resource_name` (required), `condition` (optional, default: 'Ready'), `timeout_seconds` (optional, default: 30) |

### 💡 Prompts (Guided Workflows)

Prompts are reusable templates that guide the LLM through common debugging and troubleshooting workflows.

| Prompt | Description | Parameters |
|--------|-------------|------------|
| `debug_failing_resource` | Step-by-step debugging guide for a failing resource | `resource_name` (required) |
| `analyze_resource_logs` | Analyze logs from a resource to identify errors | `resource_name` (required), `lines` (optional, default: 100) |
| `troubleshoot_startup_failure` | Investigate why a resource won't start or keeps crashing | `resource_name` (required) |
| `health_check_all_resources` | Comprehensive health check across all resources | None |
| `optimize_resource_usage` | Optimize resource usage by selectively enabling/disabling services | `focus_resources` (required, list) |

### Error Handling

All capabilities include comprehensive error handling:
- **Resource Not Found**: Raises `ValueError` with helpful message
- **Tilt Connection Issues**: Raises `RuntimeError` with Tilt error details
- **JSON Parsing Errors**: Provides detailed parsing error information

All operations are logged to `~/.tilt-mcp/tilt_mcp.log` for debugging.

## Features

**MCP Protocol Compliance:**
- 🔍 **Resources**: Read-only access to Tilt data via URI templates (e.g., `tilt://resources/all`)
- 🛠️ **Tools**: Actions with side effects for resource management and control
- 💡 **Prompts**: Guided workflows for debugging and troubleshooting

**Capabilities:**
- 📊 **Resource Discovery**: List all active Tilt resources with their current status
- 📜 **Log Retrieval**: Fetch recent logs from any Tilt resource with configurable tail
- 🔄 **Resource Triggering**: Manually trigger Tilt resources to rebuild/update
- ✅ **Resource Control**: Enable or disable resources dynamically
- 📋 **Detailed Information**: Get comprehensive details about any resource
- ⏳ **Wait Conditions**: Wait for resources to reach specific states
- 🤖 **Guided Workflows**: Pre-built prompts for common debugging scenarios

**Technical Features:**
- 🛡️ **Type Safety**: Built with Python type hints for better IDE support
- 🚀 **Async Support**: Fully asynchronous implementation using FastMCP
- 📈 **MCP Best Practices**: Proper separation of resources, tools, and prompts
- 🔧 **Comprehensive Logging**: All operations logged to `~/.tilt-mcp/tilt_mcp.log`

## Prerequisites

- Python 3.10 or higher (required by FastMCP 2.0)
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

Once configured, the Tilt MCP server provides Resources, Tools, and Prompts through the Model Context Protocol.

### Using Resources

Resources are read-only and provide direct access to Tilt data. MCP clients can access them via their URI:

**Get all resources:**
```
tilt://resources/all
```
Returns:
```json
{
  "resources": [
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
  ],
  "count": 2
}
```

**Get logs from a resource:**
```
tilt://resources/frontend/logs?tail=50
```
Returns the last 50 lines of logs as plain text.

**Get detailed resource information:**
```
tilt://resources/backend/describe
```
Returns detailed YAML/text output with configuration, status, and build history.

### Using Tools

Tools perform actions that modify the state of your Tilt environment.

**Trigger a rebuild:**
```json
{
  "name": "trigger_resource",
  "arguments": {
    "resource_name": "backend"
  }
}
```

**Enable specific resources:**
```json
{
  "name": "enable_resource",
  "arguments": {
    "resource_names": ["frontend", "backend"],
    "enable_only": false
  }
}
```

**Disable resources:**
```json
{
  "name": "disable_resource",
  "arguments": {
    "resource_names": ["frontend", "backend"]
  }
}
```

**Wait for a resource to be ready:**
```json
{
  "name": "wait_for_resource",
  "arguments": {
    "resource_name": "backend",
    "condition": "Ready",
    "timeout_seconds": 60
  }
}
```

### Using Prompts

Prompts provide guided workflows for common tasks. They generate contextual messages that guide the LLM through debugging and troubleshooting.

**Debug a failing resource:**
```json
{
  "name": "debug_failing_resource",
  "arguments": {
    "resource_name": "backend"
  }
}
```
This generates a comprehensive debugging workflow that guides the LLM to check logs, status, and suggest fixes.

**Perform a health check:**
```json
{
  "name": "health_check_all_resources",
  "arguments": {}
}
```
This creates a systematic health check workflow across all resources.

**Optimize resource usage:**
```json
{
  "name": "optimize_resource_usage",
  "arguments": {
    "focus_resources": ["backend", "database"]
  }
}
```
This guides the LLM to enable only specified resources and disable others to conserve system resources.

## Example Prompts

Here are some example prompts you can use with an AI assistant that has access to this MCP server:

**Using Built-in Prompt Templates:**
- "Use the debug_failing_resource prompt for the backend service"
- "Run a health check on all my resources"
- "Use the troubleshoot_startup_failure prompt to investigate why the frontend won't start"
- "Analyze the logs from the backend service using the analyze_resource_logs prompt"
- "Help me optimize my resources to focus on just the backend and database"

**Resource Discovery & Status:**
- "Show me all the Tilt resources that are currently running"
- "Which services are failing or have errors?"
- "Compare the status of frontend and backend services"
- "Access the tilt://resources/all resource to see all services"

**Log Analysis:**
- "Get logs from the backend-api service (last 100 lines)"
- "Read the logs from tilt://resources/frontend/logs?tail=50"
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

**Advanced Automation Workflows:**
- "Enable the backend, wait for it to be ready, then check its logs"
- "Disable all services, then enable only frontend and wait for it to start"
- "Get detailed info about the database and show me its recent logs"
- "Trigger a rebuild of the API service and wait until it's ready"
- "Run a complete health check and fix any issues you find"

**Using Resources Directly:**
- "Read tilt://resources/backend/describe to understand the configuration"
- "Compare logs from tilt://resources/frontend/logs and tilt://resources/backend/logs"
- "Check tilt://resources/all to see which services need attention"

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
