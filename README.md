# Tilt MCP Server

A Model Context Protocol (MCP) server that integrates with [Tilt](https://tilt.dev/) to provide programmatic access to Tilt resources and logs through LLM applications.

## Overview

The Tilt MCP server allows Large Language Models (LLMs) and AI assistants to interact with your Tilt development environment. It provides tools to:

- List all enabled Tilt resources
- Fetch logs from specific resources
- Monitor resource status and health

This enables AI-powered development workflows, debugging assistance, and automated monitoring of your Tilt-managed services.

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

### From PyPI (recommended)

```bash
pip install tilt-mcp
```

### From Source

```bash
git clone https://github.com/aryan-agrawal-glean/tilt-mcp.git
cd tilt-mcp
pip install -e .
```

## Configuration

### For Claude Desktop

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tilt": {
      "command": "python",
      "args": ["-m", "tilt_mcp.server"],
      "env": {}
    }
  }
}
```

### For Development/Testing

You can run the server directly:

```bash
python -m tilt_mcp.server
```

Or use it with the MCP CLI:

```bash
mcp run python -m tilt_mcp.server
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

### Debug Logging

To enable debug logging, set the environment variable:

```bash
export LOG_LEVEL=DEBUG
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
- 💬 Issues: [GitHub Issues](https://github.com/aryan-agrawal-glean/tilt-mcp/issues)
- 📖 Docs: [GitHub Wiki](https://github.com/aryan-agrawal-glean/tilt-mcp/wiki) 