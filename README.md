# Tilt MCP Server

A Model Context Protocol (MCP) server that integrates with [Tilt](https://tilt.dev/) to provide programmatic access to Tilt resources and logs through LLM applications.

## Why use a Tilt MCP server?

Imagine prompting like this:

> Please work on {some LLM request} and then check tilt MCP for "backend-api" resource logs for compile status. Make sure that "backend-tests" resource is successful with your changes.

The key insight is you no longer need to tell your LLM _how_ to build and deploy your code. Instead, you can simply ask it to _what_ to build and deploy.

Tilt is a powerful tool for working with Docker/Kubernetes workloads. With the Tilt MCP server, you can integrate Tilt's features directly into your workflow using Large Language Models (LLMs) like Claude Code / Codex / Gemini / VS Code Copilot / etc.

This saves significant LLM tokens (and so ⏱️+💰), both by avoiding to give extra context to your LLM on how to build/deploy, and also by avoiding LLMs actually doing the build/deploy. All the LLM needs to know is to make code changes then call the tilt MCP server to get real-time feedback.

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
| `tilt://resources/all{?tilt_port}` | List of all enabled Tilt resources with their current status |
| `tilt://resources/{resource_name}/logs{?tail,tilt_port}` | Logs from a specific resource (supports `?tail=N` query parameter, default: 1000) |
| `tilt://resources/{resource_name}/describe{?tilt_port}` | Detailed information about a specific resource |

All resources support an optional `tilt_port` parameter (default: 10350) to query different Tilt instances.

**Example URIs:**
- `tilt://resources/all` - Get all resources from default port (10350)
- `tilt://resources/all?tilt_port=10351` - Get all resources from port 10351
- `tilt://resources/frontend/logs` - Get last 1000 lines from frontend (default)
- `tilt://resources/frontend/logs?tail=100&tilt_port=10351` - Get last 100 lines from frontend on port 10351
- `tilt://resources/backend/describe` - Get detailed info about backend

### 🛠️ Tools (Actions with Side Effects)

Tools enable LLMs to perform actions that modify the state of your Tilt environment.

| Tool | Description | Parameters |
|------|-------------|------------|
| `trigger_resource` | Triggers a Tilt resource to rebuild/update | `resource_name` (required), `tilt_port` (optional, default: '10350') |
| `enable_resource` | Enables one or more Tilt resources | `resource_names` (required, list), `enable_only` (optional, default: false), `tilt_port` (optional, default: '10350') |
| `disable_resource` | Disables one or more Tilt resources | `resource_names` (required, list), `tilt_port` (optional, default: '10350') |
| `wait_for_resource` | Wait for a resource to reach a specific condition | `resource_name` (required), `condition` (optional, default: 'Ready'), `timeout_seconds` (optional, default: 30), `tilt_port` (optional, default: '10350') |

All tools support an optional `tilt_port` parameter to target different Tilt instances running on different ports.

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

The Docker-based installation requires no Python setup and is automatically kept up-to-date with monthly builds. The image is optimized for size using Alpine Linux (~320MB vs 545MB+ for Debian-based images - 41% reduction).

**How it works:**
- Automatically discovers the Tilt API port from `~/.tilt-dev/config` based on the `tilt_port` parameter
- Uses `socat` to dynamically create a TCP tunnel from inside the container to the host Tilt server
- Your host's `~/.tilt-dev` directory is mounted with write access (Tilt CLI needs lock files)
- A single MCP server can query multiple Tilt instances by specifying different `tilt_port` values (10350, 10351, etc.)
- The Python code handles port discovery and socat management automatically

**Note:** The image size is primarily driven by FastMCP 2.0's dependencies (cryptography, pydantic, etc.). For reference:
- Base Alpine + Python: ~50MB
- Tilt binary: ~20MB
- FastMCP 2.0 + dependencies: ~250MB

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

**For macOS/Linux (single Tilt instance on default port 10350):**
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

**For multiple Tilt instances:**

A single MCP server can query multiple Tilt instances. Simply specify the `tilt_port` parameter when calling tools or resources:

```python
# Query resources from different Tilt instances
trigger_resource(resource_name="backend", tilt_port="10350")  # First instance
trigger_resource(resource_name="backend", tilt_port="10351")  # Second instance

# Get logs from specific instance
# URI: tilt://resources/backend/logs?tilt_port=10351
```

No additional configuration needed - use the same single-instance Docker config above.

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
        "${env:USERPROFILE}\\.tilt-dev:/home/mcp-user/.tilt-dev",
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

**Key Configuration Notes:**
- The `tilt_port` parameter represents the web UI port (10350, 10351, etc.) - NOT the API port
- The Python code auto-discovers the actual API port from `~/.tilt-dev/config`
- Context naming: port 10350 → "tilt-default", port 10351 → "tilt-10351", etc.
- The `~/.tilt-dev` directory must be mounted with **write access** (Tilt CLI needs lock files)
- `socat` dynamically forwards the discovered API port to `host.docker.internal`
- `--network=host` is required for `host.docker.internal` to work on macOS/Windows

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

### Building Docker Image Locally

Build the optimized Alpine-based image:

```bash
docker build -t ghcr.io/rrmistry/tilt-mcp:latest .
```

Or build with a specific Tilt version:

```bash
docker build --build-arg TILT_VERSION=0.35.2 -t ghcr.io/rrmistry/tilt-mcp:latest .
```

To use Debian instead of Alpine (larger image but better compatibility):

```bash
docker build --build-arg BASE_IMAGE=python:3.11-slim-bookworm -t ghcr.io/rrmistry/tilt-mcp:latest .
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
tilt://resources/frontend/logs
```
Returns the last 1000 lines of logs as plain text (default).

**Get custom number of log lines:**
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
- "Get the last 100 lines of logs from the backend-api service"
- "Read the logs from tilt://resources/frontend/logs?tail=50"
- "Show me the last 200 lines of logs from any failing services"
- "Help me debug why the frontend service is crashing by looking at recent logs"

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
- "Compare logs from tilt://resources/frontend/logs?tail=500 and tilt://resources/backend/logs?tail=500"
- "Check tilt://resources/all to see which services need attention"
- "Get the last 50 lines from the frontend: tilt://resources/frontend/logs?tail=50"

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
    - Ensure your `~/.tilt-dev` directory exists and is being created by your Tilt instance
    - The directory must be mounted with write access: `~/.tilt-dev:/home/mcp-user/.tilt-dev` (Tilt CLI needs lock files)
    - The `tilt_port` parameter should be your web UI port (10350, 10351, etc.), not the random API port
    - Check the logs at `~/.tilt-mcp/tilt_mcp.log` to see the discovered API port
    - The Python code auto-discovers the API port from the config and launches `socat` automatically
    - Ensure `--network=host` is included in docker args (required for `host.docker.internal`)

5. **Alpine Linux compatibility**
    - The Docker image uses Alpine Linux for size optimization
    - Most Python packages work fine, but if you encounter issues with binary dependencies, you can build using the Debian base by changing the `BASE_IMAGE` build arg to `python:3.11-slim-bookworm`

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
