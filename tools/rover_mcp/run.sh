#!/bin/bash
# Entry point for the MCP client (.mcp.json). stdout is the MCP channel, so sourcing goes to stderr.
D=$(dirname "$(readlink -f "$0")")
source "$D/simenv.sh" >&2
exec "$D/.venv/bin/python" "$D/server.py"
