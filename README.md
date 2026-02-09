# Golemio MCP Server

An MCP server that exposes Prague's Golemio open data API to AI assistants. Query public transit departures, air quality, parking availability, and more.

## Installation

Get an API key from https://api.golemio.cz/api-keys/

Add to your MCP configuration (e.g., `~/.mcp.json`):

```json
{
  "mcpServers": {
    "golemio": {
      "command": "uvx",
      "args": ["golemio-mcp"],
      "env": {
        "GOLEMIO_API_KEY": "your-api-key"
      }
    }
  }
}
```

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) to be installed.

> **NixOS users**: `uvx` won't work due to dynamic linking. See [Development](#development) for NixOS-specific configuration.

## Available Tools

**Public Transit**
- `search_stops` - Find stops by name (works with or without Czech diacritics)
- `get_departures` - Real-time departure boards

**City Data**
- `get_air_quality_stations` - Air quality measurements
- `get_parking_lots` - Parking availability
- `get_waste_stations` - Waste container fill levels
- `get_bicycle_counters` / `get_bicycle_detections` - Bike traffic data

**Points of Interest**
- `get_medical_institutions` - Hospitals, clinics
- `get_municipal_libraries` - Public libraries
- `get_playgrounds` - Playgrounds
- `get_gardens` - Public gardens
- `get_city_districts` - District boundaries

## Development

Requires Python 3.12+ and uv.

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest -v

# Run server
uv run golemio-mcp
```

### Local MCP configuration

To run from a local clone instead of PyPI:

```json
{
  "mcpServers": {
    "golemio": {
      "command": "uv",
      "args": ["--directory", "/path/to/golemio-mcp-server", "run", "golemio-mcp"],
      "env": {
        "GOLEMIO_API_KEY": "your-api-key"
      }
    }
  }
}
```

On NixOS, use system Python to avoid dynamic linking issues:

```json
{
  "mcpServers": {
    "golemio": {
      "command": "nix-shell",
      "args": [
        "-p", "uv",
        "--run", "UV_PYTHON=/run/current-system/sw/bin/python3 uv --directory /path/to/golemio-mcp-server run golemio-mcp"
      ],
      "env": {
        "GOLEMIO_API_KEY": "your-api-key"
      }
    }
  }
}
```
