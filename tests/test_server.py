"""Tests for Tilt MCP server"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from tilt_mcp.server import get_enabled_resources


class TestGetEnabledResources:
    """Test the get_enabled_resources function"""

    @patch('subprocess.run')
    def test_get_enabled_resources_success(self, mock_run):
        """Test successful resource fetching"""
        # Mock Tilt response
        mock_response = {
            "items": [
                {
                    "metadata": {
                        "name": "frontend",
                        "labels": {"type": "k8s"}
                    },
                    "status": {
                        "runtimeStatus": "ok",
                        "updateStatus": "ok",
                        "disableStatus": {"state": "Enabled"}
                    }
                },
                {
                    "metadata": {
                        "name": "backend",
                        "labels": {"type": "k8s"}
                    },
                    "status": {
                        "runtimeStatus": "pending",
                        "updateStatus": "in_progress",
                        "disableStatus": {"state": "Enabled"}
                    }
                },
                {
                    "metadata": {
                        "name": "disabled-service",
                        "labels": {"type": "local"}
                    },
                    "status": {
                        "runtimeStatus": "ok",
                        "updateStatus": "ok",
                        "disableStatus": {"state": "Disabled"}
                    }
                }
            ]
        }

        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_response),
            stderr="",
            returncode=0
        )

        # Call function
        resources = get_enabled_resources()

        # Verify subprocess was called correctly
        mock_run.assert_called_once_with(
            ['tilt', 'get', 'uiresource', '-o', 'json'],
            capture_output=True,
            text=True,
            check=True
        )

        # Verify only enabled resources are returned
        assert len(resources) == 2
        assert resources[0]['name'] == 'frontend'
        assert resources[0]['type'] == 'k8s'
        assert resources[0]['status'] == 'ok'
        assert resources[1]['name'] == 'backend'
        assert resources[1]['status'] == 'pending'

    @patch('subprocess.run')
    def test_get_enabled_resources_command_error(self, mock_run):
        """Test handling of Tilt command errors"""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ['tilt', 'get', 'uiresource'], stderr="Tilt not running"
        )

        with pytest.raises(RuntimeError) as excinfo:
            get_enabled_resources()

        assert "Failed to fetch resources from Tilt" in str(excinfo.value)

    @patch('subprocess.run')
    def test_get_enabled_resources_invalid_json(self, mock_run):
        """Test handling of invalid JSON response"""
        mock_run.return_value = MagicMock(
            stdout="invalid json",
            stderr="",
            returncode=0
        )

        with pytest.raises(RuntimeError) as excinfo:
            get_enabled_resources()

        assert "Invalid JSON from Tilt" in str(excinfo.value)

    @patch('subprocess.run')
    def test_get_enabled_resources_empty_response(self, mock_run):
        """Test handling of empty response"""
        mock_run.return_value = MagicMock(
            stdout='{"items": []}',
            stderr="",
            returncode=0
        )

        resources = get_enabled_resources()
        assert resources == []


# Note: Additional tests would include:
# - Tests for get_resource_logs tool
# - Tests for get_all_resources tool
# - Integration tests with actual MCP client
# - Tests for error handling and edge cases
