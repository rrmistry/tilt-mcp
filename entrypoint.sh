#!/bin/bash
set -e

# Copy the host's .tilt-dev directory to the container's home directory
if [ -d "/tmp/host-tilt-dev" ]; then
    echo "Copying tilt config from /tmp/host-tilt-dev to ~/.tilt-dev..." >&2
    mkdir -p ~/.tilt-dev
    cp -r /tmp/host-tilt-dev/* ~/.tilt-dev/

    # Ensure proper permissions
    chmod -R u+w ~/.tilt-dev

    # Replace 127.0.0.1 with host.docker.internal in the config file
    if [ -f ~/.tilt-dev/config ]; then
        echo "Replacing 127.0.0.1 with host.docker.internal in tilt config..." >&2
        sed -i 's/127\.0\.0\.1/host.docker.internal/g' ~/.tilt-dev/config

        # Remove certificate-authority-data and add insecure-skip-tls-verify
        echo "Removing certificate-authority-data and adding insecure-skip-tls-verify..." >&2
        sed -i '/certificate-authority-data:/d' ~/.tilt-dev/config
        sed -i '/- cluster:/a\    insecure-skip-tls-verify: true' ~/.tilt-dev/config

        echo "Modified config server line:" >&2
        grep "server:" ~/.tilt-dev/config >&2
    fi
else
    echo "Warning: /tmp/host-tilt-dev not found, tilt may not work correctly" >&2
fi

# Execute the main command (tilt-mcp)
echo "Starting tilt-mcp..." >&2
exec "$@"
