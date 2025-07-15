# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
[Unreleased]: https://github.com/aryan-agrawal-glean/tilt-mcp/compare/v0.1.1...HEAD