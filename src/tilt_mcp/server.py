"""Tilt MCP Server - Main server implementation"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Iterator
from urllib.parse import urlparse

import yaml
from fastmcp import FastMCP

# Configure logging
# IMPORTANT: Use stderr for console logging, NOT stdout
# MCP servers use stdout for transport, so logging to stdout breaks the protocol
def _setup_logging() -> logging.Logger:
    """Configure logging handlers based on environment."""
    log_handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stderr)  # Always log to stderr (works for both local and Docker)
    ]

    is_docker = os.getenv('IS_DOCKER_MCP_SERVER', '').lower() == 'true'

    # In Docker, file logging is optional (logs are typically accessed via `docker logs`)
    # For local runs, always enable file logging for persistence
    # Can be overridden with TILT_MCP_LOG_FILE env var
    log_file_path = os.getenv('TILT_MCP_LOG_FILE')

    if log_file_path:
        # Explicit log file path provided
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handlers.append(logging.FileHandler(log_path, mode='a'))
    elif not is_docker:
        # Local environment: use default log file
        log_dir = Path.home() / ".tilt-mcp"
        log_dir.mkdir(exist_ok=True)
        log_handlers.append(logging.FileHandler(log_dir / "tilt_mcp.log", mode='a'))
    # In Docker without explicit log file: only stderr (captured by `docker logs`)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=log_handlers
    )
    return logging.getLogger(__name__)

logger = _setup_logging()


def parse_tilt_config(tilt_port: str = '10350') -> tuple[str, str]:
    """
    Parse Tilt config to discover the API server port for the specified web UI port.

    Args:
        tilt_port: The Tilt web UI port (e.g., '10350', '10351'). Defaults to '10350'.

    Returns:
        tuple[str, str]: (context_name, api_port)

    Raises:
        RuntimeError: If config cannot be parsed or context not found
    """
    config_path = Path.home() / '.tilt-dev' / 'config'

    logger.info(f'Parsing Tilt config for port {tilt_port}')

    # Determine context name based on port
    if tilt_port == '10350':
        context_name = 'tilt-default'
    else:
        context_name = f'tilt-{tilt_port}'

    logger.info(f'Looking for context: {context_name}')

    # Check if config file exists
    if not config_path.exists():
        raise RuntimeError(
            f'Tilt config file not found at {config_path}. '
            'Ensure Tilt is running and ~/.tilt-dev directory is mounted.'
        )

    try:
        # Parse YAML config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Find the matching context
        contexts = config.get('contexts', [])
        matching_context = None
        for ctx in contexts:
            if ctx.get('name') == context_name:
                matching_context = ctx
                break

        if not matching_context:
            available_contexts = [ctx.get('name') for ctx in contexts]
            raise RuntimeError(
                f'Context "{context_name}" not found in Tilt config. '
                f'Available contexts: {available_contexts}. '
                f'Ensure Tilt is running on port {tilt_port}.'
            )

        # Get cluster name from context
        cluster_name = matching_context.get('context', {}).get('cluster')
        if not cluster_name:
            raise RuntimeError(f'No cluster specified in context "{context_name}"')

        logger.info(f'Found cluster: {cluster_name}')

        # Find the matching cluster
        clusters = config.get('clusters', [])
        matching_cluster = None
        for cluster in clusters:
            if cluster.get('name') == cluster_name:
                matching_cluster = cluster
                break

        if not matching_cluster:
            raise RuntimeError(f'Cluster "{cluster_name}" not found in Tilt config')

        # Extract server URL and parse port
        server_url = matching_cluster.get('cluster', {}).get('server')
        if not server_url:
            raise RuntimeError(f'No server URL found in cluster "{cluster_name}"')

        logger.info(f'Server URL: {server_url}')

        # Parse port from URL (e.g., https://127.0.0.1:52899 -> 52899)
        parsed_url = urlparse(server_url)
        api_port = str(parsed_url.port)

        if not api_port:
            raise RuntimeError(f'Could not parse port from server URL: {server_url}')

        logger.info(f'Discovered API port: {api_port} for context: {context_name}')
        return context_name, api_port

    except yaml.YAMLError as e:
        raise RuntimeError(f'Failed to parse Tilt config YAML: {e}')
    except Exception as e:
        raise RuntimeError(f'Error parsing Tilt config: {e}')


def build_tilt_command(base_cmd: list[str], web_ui_port: str = '10350') -> list[str]:
    """
    Build a tilt CLI command with --host and --port flags.

    Args:
        base_cmd: Base command like ['tilt', 'get', 'uiresource']
        web_ui_port: The Tilt web UI port (e.g., 10350, 10351)

    Returns:
        list[str]: Complete command with connection flags
    """
    # Tilt CLI uses --port to specify the web UI port
    # It then reads ~/.tilt-dev/config to discover the actual API port
    return [base_cmd[0], '--host', 'localhost', '--port', web_ui_port] + base_cmd[1:]


def _is_port_accessible(host: str, port: str) -> bool:
    """
    Check if a TCP port is accessible (i.e., something is listening on it).

    Args:
        host: The host to check (e.g., '127.0.0.1')
        port: The port to check (e.g., '10350')

    Returns:
        True if the port is accessible, False otherwise
    """
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except Exception:
        return False


@contextmanager
def setup_socat_forwarding(web_ui_port: str, api_port: str) -> Iterator[None]:
    """
    Context manager for dynamic socat TCP forwarding in Docker environments.

    Sets up socat processes to forward container ports to the host, enabling
    communication with Tilt servers running on the host machine.

    Environment variables:
        IS_DOCKER_MCP_SERVER: Set to 'true' to indicate Docker environment
        TILT_MCP_USE_SOCAT: Force socat behavior:
            - 'true' or '1': Always use socat (even if port is accessible)
            - 'false' or '0': Never use socat (even in Docker)
            - 'auto' or unset: Auto-detect based on port accessibility (default)
        TILT_HOST: Host to forward to (default: 'host.docker.internal')

    Args:
        web_ui_port: Tilt web UI port to forward (e.g., '10350')
        api_port: Tilt API port to forward (e.g., '52899')

    Yields:
        None

    Raises:
        RuntimeError: If socat processes fail to start
    """
    is_docker = os.getenv('IS_DOCKER_MCP_SERVER', '').lower() == 'true'
    socat_mode = os.getenv('TILT_MCP_USE_SOCAT', 'auto').lower()

    # Determine if we should use socat
    use_socat = False

    if socat_mode in ('true', '1'):
        # Force socat on
        use_socat = True
        logger.debug('Socat forced ON via TILT_MCP_USE_SOCAT=true')
    elif socat_mode in ('false', '0'):
        # Force socat off
        use_socat = False
        logger.debug('Socat forced OFF via TILT_MCP_USE_SOCAT=false')
    elif not is_docker:
        # Not in Docker, no socat needed
        use_socat = False
        logger.debug('Not in Docker environment - skipping socat setup')
    else:
        # Auto-detect: check if the port is already accessible
        # If Tilt is directly accessible (e.g., Linux with host network or Docker on Linux),
        # we don't need socat. If not accessible, we need socat to bridge to host.docker.internal
        if _is_port_accessible('127.0.0.1', web_ui_port):
            use_socat = False
            logger.debug(f'Port {web_ui_port} is already accessible on localhost - skipping socat')
        else:
            use_socat = True
            logger.debug(f'Port {web_ui_port} not accessible on localhost - will use socat')

    if not use_socat:
        yield
        return

    socat_web_ui = None
    socat_api = None

    try:
        tilt_host = os.getenv('TILT_HOST', 'host.docker.internal')
        logger.info(f'Setting up socat forwarding for ports {web_ui_port} and {api_port} via {tilt_host}')

        # Launch socat #1: Forward web UI port
        socat_web_ui_cmd = [
            'socat',
            f'TCP-LISTEN:{web_ui_port},bind=127.0.0.1,fork,reuseaddr',
            f'TCP:{tilt_host}:{web_ui_port}'
        ]

        logger.debug(f'Launching socat (web UI): {" ".join(socat_web_ui_cmd)}')
        socat_web_ui = subprocess.Popen(
            socat_web_ui_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(0.1)

        if socat_web_ui.poll() is not None:
            _, stderr = socat_web_ui.communicate()
            raise RuntimeError(f'Socat (web UI port {web_ui_port}) failed to start: {stderr}')

        logger.debug(f'Socat (web UI port {web_ui_port}) started (PID: {socat_web_ui.pid})')

        # Launch socat #2: Forward API port
        socat_api_cmd = [
            'socat',
            f'TCP-LISTEN:{api_port},bind=127.0.0.1,fork,reuseaddr',
            f'TCP:{tilt_host}:{api_port}'
        ]

        logger.debug(f'Launching socat (API): {" ".join(socat_api_cmd)}')
        socat_api = subprocess.Popen(
            socat_api_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(0.1)

        if socat_api.poll() is not None:
            _, stderr = socat_api.communicate()
            raise RuntimeError(f'Socat (API port {api_port}) failed to start: {stderr}')

        logger.debug(f'Socat (API port {api_port}) started (PID: {socat_api.pid})')

        yield

    finally:
        # Cleanup: terminate both socat processes
        if socat_web_ui and socat_web_ui.poll() is None:
            logger.debug(f'Terminating socat (web UI) (PID: {socat_web_ui.pid})')
            socat_web_ui.terminate()
            try:
                socat_web_ui.wait(timeout=2)
                logger.debug('Socat (web UI) terminated gracefully')
            except subprocess.TimeoutExpired:
                logger.debug('Socat (web UI) did not terminate, killing process')
                socat_web_ui.kill()
                socat_web_ui.wait()

        if socat_api and socat_api.poll() is None:
            logger.debug(f'Terminating socat (API) (PID: {socat_api.pid})')
            socat_api.terminate()
            try:
                socat_api.wait(timeout=2)
                logger.debug('Socat (API) terminated gracefully')
            except subprocess.TimeoutExpired:
                logger.debug('Socat (API) did not terminate, killing process')
                socat_api.kill()
                socat_api.wait()


@dataclass
class AppContext:
    """Minimal application context for the Tilt MCP server"""
    is_docker: bool  # Whether running in Docker environment


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize minimal app context for the Tilt MCP server.

    Note: Socat forwarding is now managed per-call via setup_socat_forwarding()
    context manager, allowing dynamic port configuration for monitoring multiple
    Tilt instances.
    """
    logger.info("Starting Tilt MCP server")

    is_docker = os.getenv('IS_DOCKER_MCP_SERVER', '').lower() == 'true'

    socat_mode = os.getenv('TILT_MCP_USE_SOCAT', 'auto').lower()

    if socat_mode in ('true', '1'):
        logger.info("Running with TILT_MCP_USE_SOCAT=true - socat will always be used")
    elif socat_mode in ('false', '0'):
        logger.info("Running with TILT_MCP_USE_SOCAT=false - socat disabled")
    elif is_docker:
        logger.info("Running in Docker environment - socat will be auto-configured per-call based on port accessibility")
    else:
        logger.info("Running as local Python package - no socat forwarding needed")

    # Create minimal context
    ctx = AppContext(is_docker=is_docker)

    # Set global context for use by tilt CLI functions
    global _app_context
    _app_context = ctx

    try:
        yield ctx
    finally:
        logger.info("Shutting down Tilt MCP server")


# Create FastMCP server
mcp = FastMCP(
    'Tilt MCP',
    dependencies=['tilt'],
    lifespan=app_lifespan
)

# Global context holder (will be set by lifespan)
_app_context: AppContext | None = None


def get_enabled_resources(tilt_port: str = '10350') -> list[dict]:
    """
    Fetch all enabled resources from Tilt

    Args:
        tilt_port: The Tilt web UI port to query (default: '10350')

    Returns:
        list[dict]: List of enabled Tilt resources
    """
    try:
        # Discover API port from config
        _, api_port = parse_tilt_config(tilt_port)

        # Set up socat forwarding if in Docker, then fetch resources
        with setup_socat_forwarding(web_ui_port=tilt_port, api_port=api_port):
            # Build command with connection flags
            cmd = build_tilt_command(
                ['tilt', 'get', 'uiresource', '-o', 'json'],
                web_ui_port=tilt_port
            )

            result = subprocess.run(
                cmd,
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

def _all_resources_impl(tilt_port: str = '10350') -> dict:
    """Implementation for fetching all enabled Tilt resources."""
    logger.info(f'Fetching all enabled resources from port {tilt_port}')
    resources = get_enabled_resources(tilt_port)
    logger.info(f'Found {len(resources)} enabled resources on port {tilt_port}')
    return {"resources": resources, "count": len(resources), "tilt_port": tilt_port}


@mcp.resource("tilt://resources/all")
def all_resources_default() -> dict:
    """List of all enabled Tilt resources from default port (10350).

    This is the static resource that appears in listMcpResources().
    For other ports, use the template: tilt://resources/all?tilt_port=PORT
    """
    return _all_resources_impl('10350')


@mcp.resource("tilt://resources/all{?tilt_port}")
def all_resources_template(tilt_port: str = '10350') -> dict:
    """List of all enabled Tilt resources with their current status.

    Args:
        tilt_port: The Tilt web UI port (default: 10350 for backward compatibility)

    Query different Tilt instances by specifying tilt_port parameter.
    """
    return _all_resources_impl(tilt_port)


def _get_resource_logs_impl(resource_name: str, tail: int = 1000, filter: str = '', tilt_port: str = '10350') -> str:
    """Implementation for fetching logs from a specific Tilt resource.

    Args:
        resource_name: The name of the Tilt resource
        tail: Number of log lines to return after filtering (default: 1000)
        filter: Optional regex pattern to filter log lines (case-insensitive by default)
        tilt_port: The Tilt web UI port (default: 10350)

    Returns:
        Log output as a string
    """
    logger.info(f'Getting logs for resource: {resource_name} with tail: {tail}, filter: "{filter}" from port {tilt_port}')

    try:
        # Validate regex pattern if provided
        # Default to case-insensitive matching for user convenience
        # Users can override with (?-i) in their pattern if case-sensitive matching is needed
        filter_pattern = None
        if filter:
            try:
                filter_pattern = re.compile(filter, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f'Invalid regex pattern "{filter}": {e}')

        # Discover API port from config
        _, api_port = parse_tilt_config(tilt_port)

        # Set up socat forwarding if in Docker
        with setup_socat_forwarding(web_ui_port=tilt_port, api_port=api_port):
            cmd = build_tilt_command(
                ['tilt', 'logs', resource_name],
                web_ui_port=tilt_port
            )
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

            log_lines = logs.splitlines()

            # Apply regex filter if provided
            if filter_pattern:
                original_count = len(log_lines)
                log_lines = [line for line in log_lines if filter_pattern.search(line)]
                logger.info(f'Filter matched {len(log_lines)} of {original_count} log lines')

                if not log_lines:
                    return f'No logs matching filter "{filter}" for resource: {resource_name}'

            # Return only the specified number of lines (after filtering)
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
    except ValueError:
        raise  # Re-raise ValueError as-is (includes invalid regex)
    except Exception as e:
        logger.error(f'Unexpected error getting logs: {str(e)}')
        raise RuntimeError(f'Error getting logs: {str(e)}')


@mcp.resource("tilt://resources/{resource_name}/logs{?tail,filter,tilt_port}")
def resource_logs(resource_name: str, tail: int = 1000, filter: str = '', tilt_port: str = '10350') -> str:
    """Logs from a specific Tilt resource with optional regex filtering.

    Args:
        resource_name: The name of the Tilt resource
        tail: Number of log lines to return after filtering (default: 1000)
        filter: Optional regex pattern to filter log lines (case-insensitive by default).
                Only lines matching this pattern will be returned. Useful for filtering
                by X-Request-ID, error messages, or specific keywords. Examples:
                - 'X-Request-Id: abc123' - filter by request ID
                - 'error|warn' - show only errors and warnings
                - '\\[2024-01-15' - filter by date prefix
                - '(?-i)ERROR' - case-sensitive match (use (?-i) to disable case-insensitivity)
        tilt_port: The Tilt web UI port (default: 10350 for backward compatibility)

    Query different Tilt instances by specifying tilt_port parameter.
    """
    return _get_resource_logs_impl(resource_name, tail, filter, tilt_port)


def _describe_resource_impl(resource_name: str, tilt_port: str = '10350') -> str:
    """Implementation for describing a specific Tilt resource.

    Args:
        resource_name: The name of the resource to describe
        tilt_port: The Tilt web UI port (default: 10350)

    Returns:
        Resource description as a string
    """
    logger.info(f'Describing resource: {resource_name} from port {tilt_port}')

    try:
        # Discover API port from config
        _, api_port = parse_tilt_config(tilt_port)

        # Set up socat forwarding if in Docker
        with setup_socat_forwarding(web_ui_port=tilt_port, api_port=api_port):
            cmd = build_tilt_command(
                ['tilt', 'describe', 'uiresource', resource_name],
                web_ui_port=tilt_port
            )
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


@mcp.resource("tilt://resources/{resource_name}/describe{?tilt_port}")
def resource_description(resource_name: str, tilt_port: str = '10350') -> str:
    """Detailed information about a specific Tilt resource including configuration, status, and build history.

    Args:
        resource_name: The name of the resource to describe
        tilt_port: The Tilt web UI port (default: 10350 for backward compatibility)

    Query different Tilt instances by specifying tilt_port parameter.
    """
    return _describe_resource_impl(resource_name, tilt_port)


# ===== Tools (actions with side effects) =====


@mcp.tool(description="Trigger a Tilt resource to rebuild/update on a specific Tilt instance.")
def trigger_resource(
    resource_name: Annotated[str, "The name of the Tilt resource to trigger"],
    tilt_port: Annotated[str, "The Tilt web UI port (default: 10350)"] = '10350'
) -> str:
    """Trigger a Tilt resource to rebuild/update.

    Returns:
        JSON string containing the trigger result with a success message
    """
    logger.info(f'Triggering resource: {resource_name} on port {tilt_port}')

    try:
        # Discover API port from config
        _, api_port = parse_tilt_config(tilt_port)

        # Set up socat forwarding if in Docker
        with setup_socat_forwarding(web_ui_port=tilt_port, api_port=api_port):
            cmd = build_tilt_command(
                ['tilt', 'trigger', resource_name],
                web_ui_port=tilt_port
            )
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
                'tilt_port': tilt_port,
                'message': f'Resource "{resource_name}" has been triggered on port {tilt_port}',
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


@mcp.tool(description="Enable one or more Tilt resources on a specific instance. Optionally disable all others.")
def enable_resource(
    resource_names: Annotated[list[str], "List of resource names to enable"],
    enable_only: Annotated[bool, "If True, enable these resources and disable all others"] = False,
    tilt_port: Annotated[str, "The Tilt web UI port (default: 10350)"] = '10350'
) -> str:
    """Enable one or more Tilt resources.

    Returns:
        JSON string containing the result with a success message
    """
    if not resource_names:
        raise ValueError('At least one resource name must be provided')

    logger.info(f'Enabling resources: {resource_names}, only={enable_only} on port {tilt_port}')

    try:
        # Discover API port from config
        _, api_port = parse_tilt_config(tilt_port)

        # Set up socat forwarding if in Docker
        with setup_socat_forwarding(web_ui_port=tilt_port, api_port=api_port):
            base_cmd = ['tilt', 'enable']
            if enable_only:
                base_cmd.append('--only')
            base_cmd.extend(resource_names)

            cmd = build_tilt_command(
                base_cmd,
                web_ui_port=tilt_port
            )

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
                'tilt_port': tilt_port,
                'message': f'Resources {resource_names} have been enabled on port {tilt_port}' + (' (all others disabled)' if enable_only else ''),
                'output': result.stdout.strip() if result.stdout else ''
            })

    except subprocess.CalledProcessError as e:
        logger.error(f'Error enabling resources: {e.stderr}')
        raise RuntimeError(f'Failed to enable resources: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error enabling resources: {str(e)}')
        raise RuntimeError(f'Error enabling resources: {str(e)}')


@mcp.tool(description="Disable one or more Tilt resources on a specific instance.")
def disable_resource(
    resource_names: Annotated[list[str], "List of resource names to disable"],
    tilt_port: Annotated[str, "The Tilt web UI port (default: 10350)"] = '10350'
) -> str:
    """Disable one or more Tilt resources.

    Returns:
        JSON string containing the result with a success message
    """
    if not resource_names:
        raise ValueError('At least one resource name must be provided')

    logger.info(f'Disabling resources: {resource_names} on port {tilt_port}')

    try:
        # Discover API port from config
        _, api_port = parse_tilt_config(tilt_port)

        # Set up socat forwarding if in Docker
        with setup_socat_forwarding(web_ui_port=tilt_port, api_port=api_port):
            base_cmd = ['tilt', 'disable']
            base_cmd.extend(resource_names)

            cmd = build_tilt_command(
                base_cmd,
                web_ui_port=tilt_port
            )

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
                'tilt_port': tilt_port,
                'message': f'Resources {resource_names} have been disabled on port {tilt_port}',
                'output': result.stdout.strip() if result.stdout else ''
            })

    except subprocess.CalledProcessError as e:
        logger.error(f'Error disabling resources: {e.stderr}')
        raise RuntimeError(f'Failed to disable resources: {e.stderr}')
    except Exception as e:
        logger.error(f'Unexpected error disabling resources: {str(e)}')
        raise RuntimeError(f'Error disabling resources: {str(e)}')


@mcp.tool(description="List all enabled Tilt resources with their current status.")
def list_resources(
    tilt_port: Annotated[str, "The Tilt web UI port (default: 10350)"] = '10350'
) -> str:
    """List all enabled Tilt resources.

    This tool provides the same functionality as the tilt://resources/all resource,
    but exposed as a tool for better compatibility with LLM clients that don't
    support MCP resources.

    Returns:
        JSON string containing the list of resources with their status
    """
    logger.info(f'Listing all enabled resources from port {tilt_port}')
    resources = get_enabled_resources(tilt_port)
    logger.info(f'Found {len(resources)} enabled resources on port {tilt_port}')
    return json.dumps({
        'resources': resources,
        'count': len(resources),
        'tilt_port': tilt_port
    })


@mcp.tool(description="Get logs from a specific Tilt resource with optional regex filtering.")
def get_resource_logs(
    resource_name: Annotated[str, "The name of the Tilt resource"],
    tail: Annotated[int, "Number of log lines to return after filtering (default: 1000)"] = 1000,
    filter: Annotated[str, "Optional regex pattern to filter log lines (case-insensitive). Examples: 'error|warn', 'X-Request-Id: abc123'"] = '',
    tilt_port: Annotated[str, "The Tilt web UI port (default: 10350)"] = '10350'
) -> str:
    """Get logs from a specific Tilt resource with optional regex filtering.

    This tool provides the same functionality as the tilt://resources/{name}/logs resource,
    but exposed as a tool for better compatibility with LLM clients that don't
    support MCP resources.

    Returns:
        The log output as a string
    """
    return _get_resource_logs_impl(resource_name, tail, filter, tilt_port)


@mcp.tool(description="Get detailed information about a specific Tilt resource including configuration, status, and build history.")
def describe_resource(
    resource_name: Annotated[str, "The name of the resource to describe"],
    tilt_port: Annotated[str, "The Tilt web UI port (default: 10350)"] = '10350'
) -> str:
    """Get detailed information about a specific Tilt resource.

    This tool provides the same functionality as the tilt://resources/{name}/describe resource,
    but exposed as a tool for better compatibility with LLM clients that don't
    support MCP resources.

    Returns:
        The resource description as a string
    """
    return _describe_resource_impl(resource_name, tilt_port)


def _get_resource_status(resource_name: str, tilt_port: str, api_port: str) -> dict | None:
    """
    Get the current status of a specific Tilt resource.

    Args:
        resource_name: The name of the resource to query
        tilt_port: The Tilt web UI port
        api_port: The Tilt API port (for socat forwarding)

    Returns:
        dict with resource status info, or None if not found

    Status values from Tilt:
        updateStatus: "ok", "error", "pending", "in_progress", "none", "not_applicable"
        runtimeStatus: "ok", "error", "pending", "not_applicable"
        conditions[].type: "Ready", "UpToDate"
        conditions[].status: "True", "False"
        conditions[].reason: "UpdateError", "Unknown", etc. (when status is False)
        disableStatus.state: "Enabled", "Disabled"
    """
    try:
        with setup_socat_forwarding(web_ui_port=tilt_port, api_port=api_port):
            cmd = build_tilt_command(
                ['tilt', 'get', 'uiresource', resource_name, '-o', 'json'],
                web_ui_port=tilt_port
            )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)

            status = data.get('status', {})
            conditions = status.get('conditions', [])

            # Build a dict of condition name -> {status: bool, reason: str}
            condition_map = {}
            for cond in conditions:
                cond_type = cond.get('type', '')
                cond_status = cond.get('status', '') == 'True'
                cond_reason = cond.get('reason', '')
                condition_map[cond_type] = {
                    'status': cond_status,
                    'reason': cond_reason
                }

            # Extract build error if present
            build_history = status.get('buildHistory', [])
            last_build_error = None
            if build_history:
                last_build_error = build_history[0].get('error')

            # Check if resource is disabled
            disable_status = status.get('disableStatus', {})
            is_disabled = disable_status.get('state') == 'Disabled'

            return {
                'name': data.get('metadata', {}).get('name'),
                'runtimeStatus': status.get('runtimeStatus', 'unknown'),
                'updateStatus': status.get('updateStatus', 'unknown'),
                'conditions': condition_map,
                'lastBuildError': last_build_error,
                'isDisabled': is_disabled
            }

    except subprocess.CalledProcessError:
        return None
    except json.JSONDecodeError:
        return None


# Valid Tilt condition types that can be waited on
VALID_TILT_CONDITIONS = ['Ready', 'UpToDate']


@mcp.tool(description="Wait for a Tilt resource to reach a condition on a specific instance.")
def wait_for_resource(
    resource_name: Annotated[str, "The name of the resource to wait for"],
    condition: Annotated[str, "The condition to wait for (e.g., 'Ready', 'UpToDate')"] = 'Ready',
    timeout_seconds: Annotated[int, "Maximum time to wait in seconds"] = 30,
    tilt_port: Annotated[str, "The Tilt web UI port (default: 10350)"] = '10350'
) -> str:
    """Wait for a Tilt resource to reach a specific condition.

    Valid conditions:
    - 'Ready': Resource is ready and running (most common)
    - 'UpToDate': Resource has been updated to the latest version

    This function first checks if the resource is already in the target condition
    or in a terminal failure state before waiting. This handles cases where:
    - The resource has already completed (returns immediately with success)
    - The resource has already failed (returns immediately with failure details)
    - The resource is still running (waits for the condition)

    Returns:
        JSON string containing the result
    """
    # Validate condition name
    if condition not in VALID_TILT_CONDITIONS:
        raise ValueError(
            f'Invalid condition "{condition}". '
            f'Valid conditions are: {VALID_TILT_CONDITIONS}. '
            f'Note: "Updated" should be "UpToDate".'
        )

    logger.info(f'Waiting for resource: {resource_name}, condition: {condition}, timeout: {timeout_seconds}s on port {tilt_port}')

    try:
        # Discover API port from config
        _, api_port = parse_tilt_config(tilt_port)

        # Pre-check: Get current resource status to handle terminal states
        current_status = _get_resource_status(resource_name, tilt_port, api_port)

        if current_status is None:
            raise ValueError(f'Resource "{resource_name}" not found in Tilt')

        runtime_status = current_status['runtimeStatus']
        update_status = current_status['updateStatus']
        conditions = current_status['conditions']
        last_build_error = current_status.get('lastBuildError')
        is_disabled = current_status.get('isDisabled', False)

        logger.info(f'Current status for {resource_name}: runtimeStatus={runtime_status}, '
                    f'updateStatus={update_status}, conditions={conditions}, isDisabled={is_disabled}')

        # Check if resource is disabled - it will never reach any condition while disabled
        if is_disabled:
            logger.warning(f'Resource {resource_name} is disabled')
            return json.dumps({
                'success': False,
                'resource': resource_name,
                'condition': condition,
                'tilt_port': tilt_port,
                'message': f'Resource "{resource_name}" is disabled and will not reach condition "{condition}". Enable it first with enable_resource.',
                'terminal_state': True,
                'disabled': True,
                'current_status': {
                    'runtimeStatus': runtime_status,
                    'updateStatus': update_status
                }
            })

        # Check if already in the target condition
        target_condition = conditions.get(condition, {})
        if target_condition.get('status', False):
            logger.info(f'Resource {resource_name} already has condition {condition}=True')
            return json.dumps({
                'success': True,
                'resource': resource_name,
                'condition': condition,
                'tilt_port': tilt_port,
                'message': f'Resource "{resource_name}" already has condition "{condition}" on port {tilt_port}',
                'already_met': True,
                'current_status': {
                    'runtimeStatus': runtime_status,
                    'updateStatus': update_status
                }
            })

        # Check for terminal failure states that won't recover
        # From Tilt: updateStatus can be "error" when build fails, runtimeStatus can be "error" for runtime failures
        # The condition will have reason="UpdateError" when the update failed

        # Check if the condition explicitly failed (not just "not yet ready")
        condition_reason = target_condition.get('reason', '')
        is_error_condition = condition_reason in ('UpdateError', 'RuntimeError', 'Error')

        # updateStatus="error" means the build/update failed terminally
        is_update_error = update_status == 'error'

        # runtimeStatus="error" means the runtime (e.g., container) failed
        is_runtime_error = runtime_status == 'error'

        if is_update_error or is_error_condition:
            error_detail = last_build_error or f'updateStatus={update_status}'
            logger.warning(f'Resource {resource_name} has failed: {error_detail}')
            return json.dumps({
                'success': False,
                'resource': resource_name,
                'condition': condition,
                'tilt_port': tilt_port,
                'message': f'Resource "{resource_name}" has failed and will not reach condition "{condition}" without intervention',
                'terminal_state': True,
                'error': last_build_error,
                'current_status': {
                    'runtimeStatus': runtime_status,
                    'updateStatus': update_status,
                    'conditionReason': condition_reason
                }
            })

        if is_runtime_error:
            logger.warning(f'Resource {resource_name} has runtime error: runtimeStatus={runtime_status}')
            return json.dumps({
                'success': False,
                'resource': resource_name,
                'condition': condition,
                'tilt_port': tilt_port,
                'message': f'Resource "{resource_name}" has a runtime error and will not reach condition "{condition}" without intervention',
                'terminal_state': True,
                'current_status': {
                    'runtimeStatus': runtime_status,
                    'updateStatus': update_status,
                    'conditionReason': condition_reason
                }
            })

        # Resource is not in target condition and not in terminal failure - proceed with wait
        with setup_socat_forwarding(web_ui_port=tilt_port, api_port=api_port):
            base_cmd = [
                'tilt', 'wait',
                f'uiresource/{resource_name}',
                f'--for=condition={condition}',
                f'--timeout={timeout_seconds}s'
            ]

            cmd = build_tilt_command(
                base_cmd,
                web_ui_port=tilt_port
            )

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
                'tilt_port': tilt_port,
                'message': f'Resource "{resource_name}" reached condition "{condition}" on port {tilt_port}',
                'output': result.stdout.strip() if result.stdout else ''
            })

    except subprocess.CalledProcessError as e:
        if 'not found' in e.stderr.lower():
            logger.error(f'Resource not found: {resource_name}')
            raise ValueError(f'Resource "{resource_name}" not found in Tilt')
        elif 'timed out' in e.stderr.lower() or 'timeout' in e.stderr.lower():
            logger.error(f'Timeout waiting for resource: {resource_name}')
            # On timeout, fetch current status to provide better context
            try:
                final_status = _get_resource_status(resource_name, tilt_port, api_port)
                if final_status:
                    return json.dumps({
                        'success': False,
                        'resource': resource_name,
                        'condition': condition,
                        'tilt_port': tilt_port,
                        'message': f'Timeout waiting for resource "{resource_name}" to reach condition "{condition}"',
                        'timeout': True,
                        'current_status': {
                            'runtimeStatus': final_status['runtimeStatus'],
                            'updateStatus': final_status['updateStatus']
                        }
                    })
            except Exception:
                pass  # Fall through to raising the error
            raise RuntimeError(f'Timeout waiting for resource "{resource_name}" to reach condition "{condition}"')
        logger.error(f'Error waiting for resource: {e.stderr}')
        raise RuntimeError(f'Failed to wait for resource: {e.stderr}')
    except ValueError:
        raise  # Re-raise ValueError as-is
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
