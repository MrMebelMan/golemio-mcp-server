# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

This project uses `uv` for dependency management. On NixOS, run commands through nix-shell:

```bash
# Run all tests
nix-shell -p uv --run "UV_PYTHON=/run/current-system/sw/bin/python3 uv run pytest test_golemio_server.py -v"

# Run a single test
nix-shell -p uv --run "UV_PYTHON=/run/current-system/sw/bin/python3 uv run pytest test_golemio_server.py::TestGetBicycleCounters::test_success -v"

# Add dependencies
nix-shell -p uv --run "UV_PYTHON=/run/current-system/sw/bin/python3 uv add <package>"

# Run the MCP server directly
nix-shell -p uv --run "UV_PYTHON=/run/current-system/sw/bin/python3 uv run golemio_server.py"
```

## Architecture

This is an MCP (Model Context Protocol) server that exposes Prague's Golemio public data API as tools for AI assistants.

### Core Components

- **golemio_server.py**: Single-file MCP server using FastMCP. Contains:
  - `make_golemio_request()`: Async helper for all API calls, handles auth headers and parameter filtering
  - `format_geojson_features()`: Generic formatter for GeoJSON responses
  - 12 tool functions decorated with `@mcp.tool()`, each wrapping a Golemio API endpoint

### API Details

- Most endpoints use `https://api.golemio.cz/v2/`
- Parking uses `https://api.golemio.cz/v1/parkings/` (v1 API)
- PID departures use `https://api.golemio.cz/v2/pid/departureboards`
- Stop search uses static data from `https://data.pid.cz/stops/json/stops.json` (no auth required)
- Auth via `X-Access-Token` header from `GOLEMIO_API_KEY` env var
- All location-based tools accept `latlng` (lat,lng string) and `range` (meters) parameters

### Public Transit Tools

- `search_stops(name)`: Search for stops by name (diacritics-insensitive via `normalize_czech()`), returns GTFS IDs
- `get_departures(stop_ids)`: Get departures using comma-separated GTFS IDs (internally split into list for proper URL encoding)

### Testing

Tests use `respx` to mock httpx requests. Each tool has tests for:
- Successful API response parsing
- Parameter passing
- Missing API key handling
