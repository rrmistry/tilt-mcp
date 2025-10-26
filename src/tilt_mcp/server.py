"""Tilt MCP Server - Main server implementation"""

import argparse
import json
import logging
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP

# Configure logging
log_dir = Path.home() / ".tilt-mcp"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "tilt_mcp.log", mode='a')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Application context for the Tilt MCP server"""
    pass


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize app context"""
    logger.info("Starting Tilt MCP server")
    yield AppContext()
    logger.info("Shutting down Tilt MCP server")


# Create FastMCP server
mcp = FastMCP(
    'Tilt MCP',
    dependencies=['tilt'],
    lifespan=app_lifespan
)


def get_enabled_resources() -> list[dict]:
    """
    Fetch all enabled resources from Tilt
    
    Returns:
        list[dict]: List of enabled Tilt resources
    """
    try:
        result = subprocess.run(
            ['tilt', 'get', 'uiresource', '-o', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        resources = []

        for item in data.get('items', []):
            metadata = item.get('metadata', {})
            status = item.get('status', {})

            # Skip disabled resources
            if status.get('disableStatus', {}).get('state') == 'Disabled':
                continue

            resources.append({
                'name': metadata.get('name'),
                'type': metadata.get('labels', {}).get('type', 'unknown'),
                'status': status.get('runtimeStatus', 'unknown'),
                'updateStatus': status.get('updateStatus', 'unknown'),
            })

        return resources
    except subprocess.CalledProcessError as e:
        logger.error(f'Failed to run tilt command: {e.stderr}')
        raise RuntimeError(f'Failed to fetch resources from Tilt: {e.stderr}')
    except json.JSONDecodeError as e:
        logger.error(f'Failed to parse Tilt output as JSON: {e}')
        raise RuntimeError(f'Invalid JSON from Tilt: {e}')
    except Exception as e:
        logger.error(f'Unexpected error fetching resources: {e}')
        raise RuntimeError(f'Error fetching resources from Tilt: {e}')


# ===== Resources (read-only data) =====

@mcp.resource("tilt://resources/all")
async def all_resources() -> dict:
    """List of all enabled Tilt resources with their current status."""
    logger.info('Fetching all enabled resources')
    resources = get_enabled_resources()
    logger.info(f'Found {len(resources)} enabled resources')
    return {"resources": resources, "count": len(resources)}


@mcp.resource("tilt://resources/{resource_name}/logs{?tail}")
async def resource_logs(resource_name: str, tail: int = 1000) -> str:
    """Logs from a specific Tilt resource.

    Args:
        resource_name: The name of the Tilt resource
        tail: Number of log lines to return (default: 1000)
    """
    logger.info(f'Getting logs for resource: {resource_name} with tail: {tail}')

    try:
        cmd = ['tilt', 'logs', resource_name]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        logs = result.stdout
        if not logs:
            return f'No logs available for resource: {resource_name}'

        # Return only the last 'tail' lines
        log_lines = logs.splitlines()
        if len(log_lines) > tail:
            log_lines = log_lines[-tail:]

        logger.info(f'Successfully retrieved {len(log_lines)} log lines')
        return '\n'.join(log_lines)

    except subprocess.CalledProcessError as e:
        if 'No such resource' in e.stderr or 'not found' in e.stderr.lower():
            logger.error(f'Resource not found: {resource_name}')
            raise ValueError(f'Resource "{resource_name}" not found in Tilt')
        logger.error(f'Error getting logs: {e.stderr}')
        raise RuntimeError(f'Failed to get logs: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error getting logs: {str(e)}')
        raise RuntimeError(f'Error getting logs: {str(e)}')


@mcp.resource("tilt://resources/{resource_name}/describe")
async def resource_description(resource_name: str) -> str:
    """Detailed information about a specific Tilt resource including configuration, status, and build history.

    Args:
        resource_name: The name of the resource to describe
    """
    logger.info(f'Describing resource: {resource_name}')

    try:
        cmd = ['tilt', 'describe', 'uiresource', resource_name]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        logger.info(f'Successfully described resource: {resource_name}')
        return result.stdout

    except subprocess.CalledProcessError as e:
        if 'not found' in e.stderr.lower():
            logger.error(f'Resource not found: {resource_name}')
            raise ValueError(f'Resource "{resource_name}" not found in Tilt')
        logger.error(f'Error describing resource: {e.stderr}')
        raise RuntimeError(f'Failed to describe resource: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error describing resource: {str(e)}')
        raise RuntimeError(f'Error describing resource: {str(e)}')


# ===== Tools (actions with side effects) =====


@mcp.tool(description="Trigger a Tilt resource to rebuild/update. Use this to force a rebuild of a resource.")
async def trigger_resource(
    resource_name: Annotated[str, "The name of the Tilt resource to trigger"]
) -> str:
    """Trigger a Tilt resource to rebuild/update.

    Returns:
        JSON string containing the trigger result with a success message
    """
    logger.info(f'Triggering resource: {resource_name}')

    try:
        cmd = ['tilt', 'trigger', resource_name]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        logger.info(f'Successfully triggered resource: {resource_name}')
        return json.dumps({
            'success': True,
            'resource': resource_name,
            'message': f'Resource "{resource_name}" has been triggered',
            'output': result.stdout.strip() if result.stdout else ''
        })

    except subprocess.CalledProcessError as e:
        if 'No such resource' in e.stderr or 'not found' in e.stderr.lower():
            logger.error(f'Resource not found: {resource_name}')
            raise ValueError(f'Resource "{resource_name}" not found in Tilt')
        logger.error(f'Error triggering resource: {e.stderr}')
        raise RuntimeError(f'Failed to trigger resource: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error triggering resource: {str(e)}')
        raise RuntimeError(f'Error triggering resource: {str(e)}')


@mcp.tool(description="Enable one or more Tilt resources. Optionally disable all other resources.")
async def enable_resource(
    resource_names: Annotated[list[str], "List of resource names to enable"],
    enable_only: Annotated[bool, "If True, enable these resources and disable all others"] = False
) -> str:
    """Enable one or more Tilt resources.

    Returns:
        JSON string containing the result with a success message
    """
    if not resource_names:
        raise ValueError('At least one resource name must be provided')

    logger.info(f'Enabling resources: {resource_names}, only={enable_only}')

    try:
        cmd = ['tilt', 'enable']
        if enable_only:
            cmd.append('--only')
        cmd.extend(resource_names)

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        logger.info(f'Successfully enabled resources: {resource_names}')
        return json.dumps({
            'success': True,
            'resources': resource_names,
            'enable_only': enable_only,
            'message': f'Resources {resource_names} have been enabled' + (' (all others disabled)' if enable_only else ''),
            'output': result.stdout.strip() if result.stdout else ''
        })

    except subprocess.CalledProcessError as e:
        logger.error(f'Error enabling resources: {e.stderr}')
        raise RuntimeError(f'Failed to enable resources: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error enabling resources: {str(e)}')
        raise RuntimeError(f'Error enabling resources: {str(e)}')


@mcp.tool(description="Disable one or more Tilt resources. Useful for temporarily stopping services.")
async def disable_resource(
    resource_names: Annotated[list[str], "List of resource names to disable"]
) -> str:
    """Disable one or more Tilt resources.

    Returns:
        JSON string containing the result with a success message
    """
    if not resource_names:
        raise ValueError('At least one resource name must be provided')

    logger.info(f'Disabling resources: {resource_names}')

    try:
        cmd = ['tilt', 'disable']
        cmd.extend(resource_names)

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        logger.info(f'Successfully disabled resources: {resource_names}')
        return json.dumps({
            'success': True,
            'resources': resource_names,
            'message': f'Resources {resource_names} have been disabled',
            'output': result.stdout.strip() if result.stdout else ''
        })

    except subprocess.CalledProcessError as e:
        logger.error(f'Error disabling resources: {e.stderr}')
        raise RuntimeError(f'Failed to disable resources: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error disabling resources: {str(e)}')
        raise RuntimeError(f'Error disabling resources: {str(e)}')


@mcp.tool(description="Wait for a Tilt resource to reach a specific condition (e.g., Ready, Updated). Essential for automation workflows.")
async def wait_for_resource(
    resource_name: Annotated[str, "The name of the resource to wait for"],
    condition: Annotated[str, "The condition to wait for (e.g., 'Ready', 'Updated')"] = 'Ready',
    timeout_seconds: Annotated[int, "Maximum time to wait in seconds"] = 30
) -> str:
    """Wait for a Tilt resource to reach a specific condition.

    Returns:
        JSON string containing the result
    """
    logger.info(f'Waiting for resource: {resource_name}, condition: {condition}, timeout: {timeout_seconds}s')

    try:
        cmd = [
            'tilt', 'wait',
            f'uiresource/{resource_name}',
            f'--for=condition={condition}',
            f'--timeout={timeout_seconds}s'
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        logger.info(f'Resource {resource_name} reached condition {condition}')
        return json.dumps({
            'success': True,
            'resource': resource_name,
            'condition': condition,
            'message': f'Resource "{resource_name}" reached condition "{condition}"',
            'output': result.stdout.strip() if result.stdout else ''
        })

    except subprocess.CalledProcessError as e:
        if 'not found' in e.stderr.lower():
            logger.error(f'Resource not found: {resource_name}')
            raise ValueError(f'Resource "{resource_name}" not found in Tilt')
        elif 'timed out' in e.stderr.lower() or 'timeout' in e.stderr.lower():
            logger.error(f'Timeout waiting for resource: {resource_name}')
            raise RuntimeError(f'Timeout waiting for resource "{resource_name}" to reach condition "{condition}"')
        logger.error(f'Error waiting for resource: {e.stderr}')
        raise RuntimeError(f'Failed to wait for resource: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error waiting for resource: {str(e)}')
        raise RuntimeError(f'Error waiting for resource: {str(e)}')


# ===== Prompts (reusable message templates) =====


@mcp.prompt(
    description="Generate a comprehensive debugging guide for a failing Tilt resource"
)
def debug_failing_resource(resource_name: str) -> str:
    """Creates a step-by-step debugging prompt for analyzing a failing Tilt resource.

    Args:
        resource_name: The name of the Tilt resource to debug
    """
    return f"""I need help debugging the Tilt resource "{resource_name}" which appears to be failing.

Please help me investigate by:
1. First, check the resource description to understand its configuration and current state
2. Retrieve recent logs to identify any error messages or warnings
3. Analyze the resource's runtime status and update status
4. Suggest potential root causes based on the logs and status
5. Recommend specific troubleshooting steps or fixes

Let's start with getting the current state and recent logs for "{resource_name}"."""


@mcp.prompt(
    description="Generate a prompt for analyzing logs from a specific resource to identify errors"
)
def analyze_resource_logs(resource_name: str, lines: int = 100) -> str:
    """Creates a prompt to analyze logs from a Tilt resource for errors and issues.

    Args:
        resource_name: The name of the Tilt resource
        lines: Number of log lines to analyze (default: 100)
    """
    return f"""Please analyze the last {lines} lines of logs from the Tilt resource "{resource_name}" and help me:

1. Identify any error messages, warnings, or unusual patterns
2. Highlight any stack traces or exception details
3. Determine if there are recurring issues or patterns
4. Suggest what might be causing the problems
5. Recommend next steps for resolution

Please retrieve and analyze the logs for "{resource_name}"."""


@mcp.prompt(
    description="Generate a prompt for investigating why a resource won't start or keeps crashing"
)
def troubleshoot_startup_failure(resource_name: str) -> str:
    """Creates a troubleshooting prompt for resources that fail to start.

    Args:
        resource_name: The name of the Tilt resource
    """
    return f"""The Tilt resource "{resource_name}" is failing to start or keeps crashing. Please help me troubleshoot by:

1. Checking the resource's detailed description to understand its configuration
2. Examining recent logs for startup errors or crash reports
3. Looking for common startup issues such as:
   - Missing dependencies or environment variables
   - Port conflicts
   - Configuration errors
   - Resource constraints (memory, CPU)
   - Network connectivity issues
4. Comparing with the status of related or dependent resources
5. Suggesting specific fixes based on the findings

Let's investigate "{resource_name}" systematically."""


@mcp.prompt(
    description="Generate a prompt for performing a health check across all Tilt resources"
)
def health_check_all_resources() -> str:
    """Creates a comprehensive health check prompt for all Tilt resources."""
    return """Please perform a comprehensive health check of all Tilt resources:

1. List all enabled resources and their current status
2. Identify any resources that are not in a healthy state (failing, pending, or error states)
3. For each unhealthy resource:
   - Get the detailed description to understand its configuration
   - Retrieve recent logs to identify issues
   - Summarize the problem
4. Provide a priority-ordered list of issues to address
5. Suggest an action plan for getting all resources healthy

Let's start with an overview of all resources."""


@mcp.prompt(
    description="Generate a prompt for optimizing resource usage by selectively enabling/disabling services"
)
def optimize_resource_usage(focus_resources: list[str]) -> str:
    """Creates a prompt for optimizing Tilt resource usage.

    Args:
        focus_resources: List of resources that should remain enabled
    """
    resources_str = ', '.join(f'"{r}"' for r in focus_resources)
    return f"""I want to optimize my development environment by focusing on specific resources. Please help me:

1. Show the current status of all Tilt resources
2. Enable only these resources: {resources_str}
3. Disable all other resources to conserve system resources
4. Wait for the enabled resources to become ready
5. Verify that they're running correctly by checking their status and recent logs

This will help me focus on {resources_str} while reducing system load."""


def main():
    """Main entry point for the Tilt MCP server"""
    # Import version from package
    try:
        from tilt_mcp import __version__
    except ImportError:
        __version__ = "0.1.0"  # Fallback version

    parser = argparse.ArgumentParser(
        description='Tilt MCP Server - Model Context Protocol server for Tilt',
        prog='tilt-mcp'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    # Parse args - this will handle --version and --help automatically
    args = parser.parse_args()

    # If we get here, run the server
    mcp.run()


if __name__ == '__main__':
    main()
