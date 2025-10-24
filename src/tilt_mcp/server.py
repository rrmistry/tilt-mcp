"""Tilt MCP Server - Main server implementation"""

import argparse
import json
import logging
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

# Configure logging
log_dir = Path.home() / ".tilt-mcp"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "tilt_mcp.log", mode='a'),
        logging.StreamHandler(sys.stdout)
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


@mcp.tool()
async def get_resource_logs(ctx: Context, resource_name: str, tail: int = 1000) -> str:
    """
    Get logs from a specific Tilt resource
    
    Args:
        resource_name: The name of the Tilt resource to get logs from
        tail: The number of lines of logs to return (default: 1000)
        
    Returns:
        str: JSON string containing the logs
        
    Raises:
        ValueError: If the resource is not found
        RuntimeError: If there's an error fetching logs
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
            return json.dumps({'logs': f'No logs available for resource: {resource_name}'})

        # Return only the last 'tail' lines
        log_lines = logs.splitlines()
        if len(log_lines) > tail:
            log_lines = log_lines[-tail:]

        logger.info(f'Successfully retrieved {len(log_lines)} log lines')
        return json.dumps({'logs': '\n'.join(log_lines)})

    except subprocess.CalledProcessError as e:
        if 'No such resource' in e.stderr or 'not found' in e.stderr.lower():
            logger.error(f'Resource not found: {resource_name}')
            raise ValueError(f'Resource "{resource_name}" not found in Tilt')
        logger.error(f'Error getting logs: {e.stderr}')
        raise RuntimeError(f'Failed to get logs: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error getting logs: {str(e)}')
        raise RuntimeError(f'Error getting logs: {str(e)}')


@mcp.tool()
async def get_all_resources(ctx: Context) -> str:
    """
    Get all enabled Tilt resources

    Returns:
        str: JSON string containing a list of resource information:
            - name: Resource name
            - type: Resource type (e.g., 'k8s', 'local', etc.)
            - status: Current runtime status
            - updateStatus: Current update status

    Raises:
        RuntimeError: If there's an error fetching resources
    """
    logger.info('Fetching all enabled resources')
    resources = get_enabled_resources()
    logger.info(f'Found {len(resources)} enabled resources')
    return json.dumps(resources, indent=2)


@mcp.tool()
async def trigger_resource(ctx: Context, resource_name: str) -> str:
    """
    Trigger a Tilt resource to rebuild/update

    Args:
        resource_name: The name of the Tilt resource to trigger

    Returns:
        str: JSON string containing the trigger result with a success message

    Raises:
        ValueError: If the resource is not found
        RuntimeError: If there's an error triggering the resource
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
