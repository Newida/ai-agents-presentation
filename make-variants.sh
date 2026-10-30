#!/usr/bin/env bash
# Convenience entry point; use optional theme names to build only those designs.
set -euo pipefail
exec "$(dirname "$0")/variants/build.sh" "$@"
