ARG BASE_IMAGE=docker.io/library/python:3.11-slim-bookworm

# Build stage
FROM ${BASE_IMAGE} AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY pyproject.toml ./
COPY src/ ./src/

# Install build tools
RUN pip install --no-cache-dir build

# Build the package
RUN python -m build --wheel

# Runtime stage
FROM ${BASE_IMAGE} AS runtime

# Install tilt CLI and runtime dependencies
RUN apt-get update && apt-get install -y \
    # Required to download the Tilt install script
    curl \
    # Required by Tilt's install.sh script
    sudo \
    # Run the Tilt install script
    && curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash mcp-user

# Set working directory
WORKDIR /app

# Copy wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/

# Install the package
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

# Create log directory
RUN mkdir -p /home/mcp-user/.tilt-mcp && \
    chown -R mcp-user:mcp-user /home/mcp-user/.tilt-mcp

# Switch to non-root user
USER mcp-user

# Set environment variables for MCP
ENV MCP_TRANSPORT=stdio

# Default command to run the MCP server
ENTRYPOINT ["tilt-mcp"]