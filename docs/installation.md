# Installation Guide

This guide covers various ways to install and configure the Tilt MCP server.

## Prerequisites

Before installing Tilt MCP, ensure you have:

1. **Python 3.8 or higher**
   ```bash
   python --version  # Should show 3.8+
   ```

2. **Tilt installed and working**
   ```bash
   tilt version  # Should show Tilt version
   ```

3. **pip package manager**
   ```bash
   pip --version
   ```

## Installation Methods

### Method 1: Install from PyPI (Recommended)

The simplest way to install Tilt MCP is from PyPI:

```bash
pip install tilt-mcp
```

To install a specific version:

```bash
pip install tilt-mcp==0.1.0
```

### Method 2: Install from Source

For the latest development version or to contribute:

```bash
# Clone the repository
git clone https://github.com/aryan-agrawal-glean/tilt-mcp.git
cd tilt-mcp

# Install in editable mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Method 3: Install from GitHub

To install directly from GitHub:

```bash
# Latest from main branch
pip install git+https://github.com/aryan-agrawal-glean/tilt-mcp.git

# Specific branch or tag
pip install git+https://github.com/aryan-agrawal-glean/tilt-mcp.git@v0.1.0
```

## Configuration

### Claude Desktop Configuration

1. Locate your Claude Desktop configuration file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/claude/claude_desktop_config.json`

2. Open the file in a text editor (create it if it doesn't exist)

3. Add the Tilt MCP server configuration:

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

4. If you have multiple MCP servers, add Tilt to the existing configuration:

```json
{
  "mcpServers": {
    "existing-server": {
      "command": "...",
      "args": ["..."]
    },
    "tilt": {
      "command": "python",
      "args": ["-m", "tilt_mcp.server"],
      "env": {}
    }
  }
}
```

5. Restart Claude Desktop for the changes to take effect

### Environment Variables

You can configure the server behavior using environment variables:

```json
{
  "mcpServers": {
    "tilt": {
      "command": "python",
      "args": ["-m", "tilt_mcp.server"],
      "env": {
        "LOG_LEVEL": "DEBUG",  // Set logging level
        "TILT_CONTEXT": "my-cluster"  // Specify Tilt context
      }
    }
  }
}
```

### Virtual Environment Setup

If you're using a virtual environment:

1. Create and activate a virtual environment:
   ```bash
   python -m venv tilt-mcp-env
   source tilt-mcp-env/bin/activate  # On Windows: tilt-mcp-env\Scripts\activate
   ```

2. Install Tilt MCP in the virtual environment:
   ```bash
   pip install tilt-mcp
   ```

3. Update Claude Desktop config to use the virtual environment:
   ```json
   {
     "mcpServers": {
       "tilt": {
         "command": "/path/to/tilt-mcp-env/bin/python",
         "args": ["-m", "tilt_mcp.server"],
         "env": {}
       }
     }
   }
   ```

## Verification

### Testing the Installation

1. Run the server manually to verify it starts:
   ```bash
   python -m tilt_mcp.server
   ```
   
   You should see startup logs indicating the server is running.

2. Check that Tilt is accessible:
   ```bash
   tilt get uiresource
   ```

### Testing with MCP CLI

If you have the MCP CLI installed:

```bash
# Test the server
mcp run python -m tilt_mcp.server

# In another terminal, interact with the server
mcp call tilt get_all_resources
```

### Verifying Claude Desktop Integration

1. Open Claude Desktop
2. Start a new conversation
3. Ask: "Can you list all my Tilt resources?"
4. Claude should use the Tilt MCP tool to fetch and display your resources

## Troubleshooting

### Common Installation Issues

#### "Module not found" error

If you get `ModuleNotFoundError: No module named 'tilt_mcp'`:

1. Verify installation:
   ```bash
   pip list | grep tilt-mcp
   ```

2. Check Python path:
   ```bash
   python -c "import sys; print(sys.path)"
   ```

3. Reinstall:
   ```bash
   pip uninstall tilt-mcp
   pip install tilt-mcp
   ```

#### Permission errors

On Unix systems, you might need to use `sudo` or install in user space:

```bash
# User installation
pip install --user tilt-mcp

# Or with sudo (not recommended)
sudo pip install tilt-mcp
```

#### Claude Desktop doesn't recognize the server

1. Verify the config file is valid JSON:
   ```bash
   python -m json.tool < ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. Check the command path is correct:
   ```bash
   which python
   ```

3. Look for errors in Claude Desktop logs

### Getting Help

If you encounter issues:

1. Check the [GitHub Issues](https://github.com/aryan-agrawal-glean/tilt-mcp/issues)
2. Review logs at `~/.tilt-mcp/tilt_mcp.log`
3. Run with debug logging:
   ```bash
   LOG_LEVEL=DEBUG python -m tilt_mcp.server
   ```

## Next Steps

- Read the [Usage Guide](../README.md#usage) to learn about available tools
- Check out [Examples](../examples/) for common use cases
- See [Development Guide](development.md) to contribute 