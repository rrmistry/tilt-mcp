#!/usr/bin/env python3
"""
Basic usage examples for Tilt MCP server

This script demonstrates how to interact with the Tilt MCP server
programmatically using the MCP client.
"""

import asyncio
import json

# Note: In a real implementation, you would use an MCP client library
# This is a simplified example showing the expected request/response format

async def example_get_all_resources():
    """Example: Get all enabled Tilt resources"""
    print("=== Get All Resources Example ===")

    # This would be an actual MCP tool call in practice
    request = {
        "tool": "get_all_resources",
        "arguments": {}
    }

    # Example response
    response = [
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
        },
        {
            "name": "postgres",
            "type": "docker_compose",
            "status": "ok",
            "updateStatus": "ok"
        }
    ]

    print(f"Request: {json.dumps(request, indent=2)}")
    print(f"Response: {json.dumps(response, indent=2)}")

    # Process the response
    healthy_resources = [r for r in response if r['status'] == 'ok']
    print(f"\nHealthy resources: {len(healthy_resources)}/{len(response)}")

    return response


async def example_get_resource_logs():
    """Example: Get logs from a specific resource"""
    print("\n=== Get Resource Logs Example ===")

    # Get logs from the frontend service
    request = {
        "tool": "get_resource_logs",
        "arguments": {
            "resource_name": "frontend",
            "tail": 50
        }
    }

    # Example response
    response = {
        "logs": """2024-01-15 10:23:45 INFO Starting server on port 3000
2024-01-15 10:23:46 INFO Webpack compilation started
2024-01-15 10:23:48 INFO Webpack compiled successfully
2024-01-15 10:23:48 INFO Server ready at http://localhost:3000
2024-01-15 10:24:01 INFO GET / 200 45ms
2024-01-15 10:24:01 INFO GET /static/js/bundle.js 200 12ms
2024-01-15 10:24:15 INFO WebSocket connection established
2024-01-15 10:24:20 INFO GET /api/health 200 5ms"""
    }

    print(f"Request: {json.dumps(request, indent=2)}")
    print("Response logs preview:")
    print(response['logs'][:200] + "..." if len(response['logs']) > 200 else response['logs'])

    return response


async def example_debug_failing_service():
    """Example: Debug a failing service by checking its logs"""
    print("\n=== Debug Failing Service Example ===")

    # First, get all resources to find failing ones
    resources = await example_get_all_resources()

    # Find services that aren't healthy
    failing_services = [r for r in resources if r['status'] != 'ok']

    if failing_services:
        print(f"\nFound {len(failing_services)} failing service(s)")

        for service in failing_services:
            print(f"\nChecking logs for failing service: {service['name']}")

            # Get logs for the failing service
            request = {
                "tool": "get_resource_logs",
                "arguments": {
                    "resource_name": service['name'],
                    "tail": 100
                }
            }

            # Example error logs
            if service['name'] == 'backend-api':
                response = {
                    "logs": """2024-01-15 10:25:01 ERROR Failed to connect to database
2024-01-15 10:25:01 ERROR Connection refused: postgresql://localhost:5432
2024-01-15 10:25:02 INFO Retrying database connection...
2024-01-15 10:25:03 ERROR Maximum retry attempts reached
2024-01-15 10:25:03 FATAL Application shutting down due to database connection failure"""
                }

                print("Found error in logs:")
                print(response['logs'])
                print("\nDiagnosis: Backend API cannot connect to PostgreSQL database")


async def example_monitor_deployment():
    """Example: Monitor a deployment by checking resource status"""
    print("\n=== Monitor Deployment Example ===")

    print("Monitoring deployment progress...")

    # Simulate checking resources multiple times
    for i in range(3):
        if i > 0:
            await asyncio.sleep(2)  # Wait between checks

        print(f"\nCheck #{i+1}:")

        request = {
            "tool": "get_all_resources",
            "arguments": {}
        }

        # Simulate deployment progress
        if i == 0:
            response = [
                {"name": "frontend", "type": "k8s", "status": "pending", "updateStatus": "in_progress"},
                {"name": "backend-api", "type": "k8s", "status": "ok", "updateStatus": "ok"},
            ]
        elif i == 1:
            response = [
                {"name": "frontend", "type": "k8s", "status": "pending", "updateStatus": "in_progress"},
                {"name": "backend-api", "type": "k8s", "status": "ok", "updateStatus": "ok"},
            ]
        else:
            response = [
                {"name": "frontend", "type": "k8s", "status": "ok", "updateStatus": "ok"},
                {"name": "backend-api", "type": "k8s", "status": "ok", "updateStatus": "ok"},
            ]

        for resource in response:
            status_icon = "✅" if resource['status'] == 'ok' else "⏳"
            print(f"  {status_icon} {resource['name']}: {resource['status']} (update: {resource['updateStatus']})")

    print("\nDeployment complete! All resources are healthy.")


async def main():
    """Run all examples"""
    print("Tilt MCP Server - Usage Examples")
    print("================================\n")

    # Run examples
    await example_get_all_resources()
    await example_get_resource_logs()
    await example_debug_failing_service()
    await example_monitor_deployment()

    print("\n================================")
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
