ARG BASE_IMAGE=docker.io/library/python:3.11-alpine
ARG TILT_VERSION=0.35.2

# Build stage
FROM ${BASE_IMAGE} AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev python3-dev

# Set working directory
WORKDIR /app

# Copy package files
COPY pyproject.toml ./
COPY src/ ./src/

# Install build tools and build the package
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip uninstall -y build

# Runtime stage
FROM ${BASE_IMAGE} AS runtime

ARG TILT_VERSION

# Install Tilt binary directly (no curl/sudo needed in final image)
RUN apk add --no-cache --virtual .download-deps wget tar && \
    ARCH=$(uname -m) && \
    case ${ARCH} in \
        aarch64) TILT_ARCH=arm64 ;; \
        x86_64) TILT_ARCH=x86_64 ;; \
        armv7l) TILT_ARCH=arm ;; \
        *) echo "Unsupported architecture: ${ARCH}" && exit 1 ;; \
    esac && \
    wget -qO- "https://github.com/tilt-dev/tilt/releases/download/v${TILT_VERSION}/tilt.${TILT_VERSION}.linux-alpine.${TILT_ARCH}.tar.gz" | tar -xz -C /usr/local/bin && \
    apk del .download-deps

# Create non-root user (Alpine uses adduser instead of useradd)
RUN adduser -D -h /home/mcp-user -s /bin/sh mcp-user

# Set working directory
WORKDIR /app

# Copy wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/

# Install the package and clean up aggressively in one layer
RUN apk add --no-cache binutils && \
    pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl /root/.cache && \
    # Remove pip and setuptools (entry points are already created)
    rm -rf /usr/local/lib/python*/site-packages/pip* && \
    rm -rf /usr/local/lib/python*/site-packages/setuptools* && \
    rm -rf /usr/local/lib/python*/site-packages/pkg_resources && \
    # Remove all __pycache__ directories and .pyc files
    find /usr/local -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local -type f -name '*.pyc' -delete && \
    find /usr/local -type f -name '*.pyo' -delete && \
    # Remove tests from installed packages
    find /usr/local/lib/python*/site-packages -type d -name tests -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python*/site-packages -type d -name test -exec rm -rf {} + 2>/dev/null || true && \
    # Strip debug symbols from shared libraries
    find /usr/local -name "*.so" -exec strip --strip-debug {} + 2>/dev/null || true && \
    # Remove binutils after stripping
    apk del binutils

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Create log directory
RUN mkdir -p /home/mcp-user/.tilt-mcp && \
    chown -R mcp-user:mcp-user /home/mcp-user/.tilt-mcp

# This host variable combined with "--network=host" when calling docker run will allow the MCP server to connect to Tilt outside the container
ENV TILT_HOST=host.docker.internal \
    TILT_PORT=10350 \
    MCP_TRANSPORT=stdio \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER mcp-user

# Use entrypoint script to copy and modify tilt config
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command to run the MCP server
CMD ["tilt-mcp"]