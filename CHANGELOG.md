# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2025-10-25

### Breaking Changes
- **Minimum Python version increased from 3.8 to 3.10** (required by FastMCP 2.0)
- Upgraded FastMCP dependency from >=0.1.0 to >=2.0.0

### Added
- **MCP Resources** (read-only data access via URIs):
  - `tilt://resources/all` - List all enabled Tilt resources
  - `tilt://resources/{resource_name}/logs{?tail}` - Get logs from any resource with optional tail parameter
  - `tilt://resources/{resource_name}/describe` - Get detailed resource information
- **New Tools** (actions with side effects):
  - `enable_resource` - Enable one or more resources, with optional "enable only" mode
  - `disable_resource` - Disable one or more resources
  - `wait_for_resource` - Wait for a resource to reach a specific condition (e.g., Ready)
  - Enhanced `trigger_resource` with better descriptions
- **MCP Prompts** (guided workflows):
  - `debug_failing_resource` - Step-by-step debugging guide for failing resources
  - `analyze_resource_logs` - Log analysis workflow for error identification
  - `troubleshoot_startup_failure` - Investigate startup and crash issues
  - `health_check_all_resources` - Comprehensive health check across all resources
  - `optimize_resource_usage` - Optimize by selectively enabling/disabling services

### Changed
- Migrated from Tools-only to full MCP protocol with Resources, Tools, and Prompts
- Converted `get_all_resources`, `get_resource_logs`, and `describe_resource` from tools to resources
- All tools now have explicit descriptions using `@mcp.tool(description=...)`
- All tool parameters now use `Annotated` types for better documentation
- Updated documentation to reflect new MCP architecture
- Tool configuration now targets Python 3.10 (black, mypy)

### Improved
- Better separation of concerns (read operations as resources, write operations as tools)
- More efficient LLM access to read-only data through resources
- Enhanced debugging experience with guided prompt workflows
- Comprehensive documentation of all MCP capabilities

## [0.1.2] - 2024-01-15

### Fixed
- Fixed type mismatch issue where MCP tools were returning dictionaries instead of JSON strings
- Both `get_all_resources` and `get_resource_logs` now return JSON-formatted strings

### Changed
- Tool return types changed from `dict` and `list[dict]` to `str` (JSON format)

## [0.1.1] - 2024-01-15

### Fixed
- Added proper command-line argument handling for `--version` and `--help` flags
- Fixed issue where the server would start immediately even when just checking version

### Changed
- The main entry point now uses argparse to handle CLI arguments properly

## [0.1.0] - 2024-01-15

### Added
- Initial release of Tilt MCP server
- `get_all_resources` tool to list enabled Tilt resources
- `get_resource_logs` tool to fetch logs from specific resources
- Comprehensive logging support
- Full async/await support using FastMCP
- Type hints throughout the codebase
- Basic test suite
- Documentation and examples

### Features
- Lists all enabled Tilt resources with their status
- Fetches recent logs from any Tilt resource
- Filters out disabled resources automatically
- Provides structured JSON responses
- Configurable log output (number of lines)
- Error handling for missing resources

[0.1.0]: https://github.com/aryan-agrawal-glean/tilt-mcp/releases/tag/v0.1.0
[0.1.1]: https://github.com/aryan-agrawal-glean/tilt-mcp/releases/tag/v0.1.1
[0.1.2]: https://github.com/aryan-agrawal-glean/tilt-mcp/releases/tag/v0.1.2
[0.1.3]: https://github.com/aryan-agrawal-glean/tilt-mcp/releases/tag/v0.1.3
[Unreleased]: https://github.com/aryan-agrawal-glean/tilt-mcp/compare/v0.1.3...HEAD