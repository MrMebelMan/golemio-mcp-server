"""Golemio MCP Server - Exposes Prague's Golemio API as tools for AI assistants."""

import json
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("golemio")

GOLEMIO_API_BASE = "https://api.golemio.cz"


def get_api_key() -> str:
    """Get the API key from environment variable."""
    return os.environ.get("GOLEMIO_API_KEY", "")


async def make_golemio_request(
    endpoint: str, params: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Make a request to the Golemio API.

    Args:
        endpoint: API endpoint path (e.g., "/v2/bicyclecounters/")
        params: Optional query parameters

    Returns:
        JSON response data or None if request fails
    """
    api_key = get_api_key()
    if not api_key:
        return None

    headers = {"X-Access-Token": api_key, "Accept": "application/json"}

    # Filter out None values from params
    if params:
        params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GOLEMIO_API_BASE}{endpoint}",
            headers=headers,
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


def format_geojson_features(data: dict[str, Any], feature_formatter: callable) -> str:
    """Format GeoJSON features into a readable string.

    Args:
        data: GeoJSON response data
        feature_formatter: Function to format individual features

    Returns:
        Formatted string representation
    """
    features = data.get("features", [])
    if not features:
        return "No results found."

    results = []
    for feature in features:
        results.append(feature_formatter(feature))

    return "\n\n".join(results)


@mcp.tool()
async def get_bicycle_counters(
    latlng: str | None = None,
    range: int | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get bicycle counting stations in Prague.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
    """
    params = {"limit": limit, "offset": offset, "latlng": latlng, "range": range}

    try:
        data = await make_golemio_request("/v2/bicyclecounters/", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_counter(feature: dict) -> str:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"Direction: {props.get('directions', 'N/A')}\n"
            f"Location: {coords[1]}, {coords[0]}" if len(coords) >= 2 else ""
        )

    return format_geojson_features(data, format_counter)


@mcp.tool()
async def get_bicycle_detections(
    id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    aggregate: bool | None = None,
) -> str:
    """Get bicycle traffic detection data from counting stations.

    Args:
        id: Counter ID to get detections for
        from_date: Start date in ISO format (e.g. "2024-01-01T00:00:00Z")
        to_date: End date in ISO format (e.g. "2024-01-31T23:59:59Z")
        aggregate: Whether to aggregate the results
    """
    params = {"id": id, "from": from_date, "to": to_date, "aggregate": aggregate}

    try:
        data = await make_golemio_request("/v2/bicyclecounters/detections", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    # Detection data format varies based on aggregation
    if isinstance(data, list):
        if not data:
            return "No detection data found."
        results = []
        for detection in data[:20]:  # Limit output
            results.append(
                f"Time: {detection.get('measured_from', 'N/A')}\n"
                f"Count: {detection.get('value', 0)}"
            )
        return "\n\n".join(results)

    return json.dumps(data, indent=2)


@mcp.tool()
async def get_air_quality_stations(
    latlng: str | None = None,
    range: int | None = None,
    districts: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get air quality monitoring stations in Prague.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        districts: Filter by district codes (comma-separated)
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
    """
    params = {
        "limit": limit,
        "offset": offset,
        "latlng": latlng,
        "range": range,
        "districts": districts,
    }

    try:
        data = await make_golemio_request("/v2/airqualitystations/", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_station(feature: dict) -> str:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        measurements = props.get("measurement", {})

        measurement_str = ""
        if measurements:
            components = measurements.get("components", [])
            if components:
                measurement_str = "\nMeasurements:\n" + "\n".join(
                    f"  - {c.get('type', 'N/A')}: {c.get('value', 'N/A')} (AQI: {c.get('aqi_level', 'N/A')})"
                    for c in components[:5]
                )

        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"District: {props.get('district', 'N/A')}\n"
            f"Location: {coords[1]}, {coords[0]}" + measurement_str
            if len(coords) >= 2
            else ""
        )

    return format_geojson_features(data, format_station)


@mcp.tool()
async def get_waste_stations(
    latlng: str | None = None,
    range: int | None = None,
    limit: int = 10,
    offset: int = 0,
    onlyMonitored: bool | None = None,
    districts: str | None = None,
) -> str:
    """Get sorted waste collection stations in Prague.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
        onlyMonitored: Filter to only monitored stations
        districts: Filter by district codes (comma-separated)
    """
    params = {
        "limit": limit,
        "offset": offset,
        "latlng": latlng,
        "range": range,
        "onlyMonitored": onlyMonitored,
        "districts": districts,
    }

    try:
        data = await make_golemio_request("/v2/sortedwastestations", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_station(feature: dict) -> str:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        containers = props.get("containers", [])

        container_str = ""
        if containers:
            container_str = "\nContainers:\n" + "\n".join(
                f"  - {c.get('trash_type', {}).get('description', 'Unknown')}: {c.get('occupancy', {}).get('percent', 'N/A')}% full"
                for c in containers[:5]
            )

        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"Address: {props.get('address', {}).get('address_formatted', 'N/A')}\n"
            f"Location: {coords[1]}, {coords[0]}" + container_str
            if len(coords) >= 2
            else ""
        )

    return format_geojson_features(data, format_station)


@mcp.tool()
async def get_parking_lots(
    latlng: str | None = None,
    range: int | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get parking lot information and availability in Prague.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
    """
    params = {"limit": limit, "offset": offset, "latlng": latlng, "range": range}

    try:
        # Note: Parking uses v1 API
        data = await make_golemio_request("/v1/parkings/", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_parking(feature: dict) -> str:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])

        total = props.get("total_num_of_places", "N/A")
        free = props.get("num_of_free_places", "N/A")

        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"Type: {props.get('parking_type', {}).get('description', 'N/A')}\n"
            f"Capacity: {free} free / {total} total\n"
            f"Location: {coords[1]}, {coords[0]}" if len(coords) >= 2 else ""
        )

    return format_geojson_features(data, format_parking)


@mcp.tool()
async def get_city_districts(
    latlng: str | None = None,
    range: int | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get Prague city district information.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
    """
    params = {"limit": limit, "offset": offset, "latlng": latlng, "range": range}

    try:
        data = await make_golemio_request("/v2/citydistricts/", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_district(feature: dict) -> str:
        props = feature.get("properties", {})
        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"Slug: {props.get('slug', 'N/A')}"
        )

    return format_geojson_features(data, format_district)


@mcp.tool()
async def get_medical_institutions(
    latlng: str | None = None,
    range: int | None = None,
    districts: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get healthcare facilities in Prague.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        districts: Filter by district codes (comma-separated)
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
    """
    params = {
        "limit": limit,
        "offset": offset,
        "latlng": latlng,
        "range": range,
        "districts": districts,
    }

    try:
        data = await make_golemio_request("/v2/medicalinstitutions/", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_institution(feature: dict) -> str:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"Type: {props.get('type', 'N/A')}\n"
            f"Address: {props.get('address', {}).get('address_formatted', 'N/A')}\n"
            f"Phone: {props.get('telephone', 'N/A')}\n"
            f"Email: {props.get('email', 'N/A')}\n"
            f"Location: {coords[1]}, {coords[0]}" if len(coords) >= 2 else ""
        )

    return format_geojson_features(data, format_institution)


@mcp.tool()
async def get_municipal_libraries(
    latlng: str | None = None,
    range: int | None = None,
    districts: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get public library locations in Prague.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        districts: Filter by district codes (comma-separated)
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
    """
    params = {
        "limit": limit,
        "offset": offset,
        "latlng": latlng,
        "range": range,
        "districts": districts,
    }

    try:
        data = await make_golemio_request("/v2/municipallibraries/", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_library(feature: dict) -> str:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"Address: {props.get('address', {}).get('address_formatted', 'N/A')}\n"
            f"Phone: {props.get('telephone', 'N/A')}\n"
            f"Email: {props.get('email', 'N/A')}\n"
            f"Web: {props.get('web', {}).get('url', 'N/A')}\n"
            f"Location: {coords[1]}, {coords[0]}" if len(coords) >= 2 else ""
        )

    return format_geojson_features(data, format_library)


@mcp.tool()
async def get_playgrounds(
    latlng: str | None = None,
    range: int | None = None,
    districts: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get public playground locations in Prague.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        districts: Filter by district codes (comma-separated)
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
    """
    params = {
        "limit": limit,
        "offset": offset,
        "latlng": latlng,
        "range": range,
        "districts": districts,
    }

    try:
        data = await make_golemio_request("/v2/playgrounds/", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_playground(feature: dict) -> str:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"Type: {props.get('type', 'N/A')}\n"
            f"District: {props.get('district', 'N/A')}\n"
            f"Address: {props.get('address', {}).get('address_formatted', 'N/A')}\n"
            f"Location: {coords[1]}, {coords[0]}" if len(coords) >= 2 else ""
        )

    return format_geojson_features(data, format_playground)


@mcp.tool()
async def get_gardens(
    latlng: str | None = None,
    range: int | None = None,
    districts: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get public garden locations in Prague.

    Args:
        latlng: Coordinates as "latitude,longitude" (e.g. "50.0890,14.4168")
        range: Search radius in meters from the coordinates
        districts: Filter by district codes (comma-separated)
        limit: Maximum number of results (default: 10)
        offset: Number of results to skip for pagination
    """
    params = {
        "limit": limit,
        "offset": offset,
        "latlng": latlng,
        "range": range,
        "districts": districts,
    }

    try:
        data = await make_golemio_request("/v2/gardens/", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    def format_garden(feature: dict) -> str:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        return (
            f"Name: {props.get('name', 'Unknown')}\n"
            f"ID: {props.get('id', 'N/A')}\n"
            f"Type: {props.get('type', 'N/A')}\n"
            f"Description: {props.get('description', 'N/A')}\n"
            f"District: {props.get('district', 'N/A')}\n"
            f"Location: {coords[1]}, {coords[0]}" if len(coords) >= 2 else ""
        )

    return format_geojson_features(data, format_garden)


def normalize_czech(text: str) -> str:
    """Normalize Czech characters for search (remove diacritics)."""
    replacements = {
        "á": "a", "č": "c", "ď": "d", "é": "e", "ě": "e", "í": "i",
        "ň": "n", "ó": "o", "ř": "r", "š": "s", "ť": "t", "ú": "u",
        "ů": "u", "ý": "y", "ž": "z",
        "Á": "a", "Č": "c", "Ď": "d", "É": "e", "Ě": "e", "Í": "i",
        "Ň": "n", "Ó": "o", "Ř": "r", "Š": "s", "Ť": "t", "Ú": "u",
        "Ů": "u", "Ý": "y", "Ž": "z",
    }
    result = text.lower()
    for czech, ascii_char in replacements.items():
        result = result.replace(czech, ascii_char)
    return result


@mcp.tool()
async def search_stops(name: str, limit: int = 10) -> str:
    """Search for Prague public transit stops by name.

    Args:
        name: Stop name to search for (case-insensitive, diacritics-insensitive).
              Examples: "Letňany", "Letnany", "mustek", "Můstek" all work.
        limit: Maximum number of results (default: 10)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://data.pid.cz/stops/json/stops.json",
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        return f"Error fetching stops: {e.response.status_code}"
    except Exception as e:
        return f"Error fetching stops: {str(e)}"

    # Search for matching stop groups (diacritics-insensitive)
    search_term = normalize_czech(name)
    matches = []

    for group in data.get("stopGroups", []):
        group_name = group.get("name", "")
        if search_term in normalize_czech(group_name):
            # Collect all GTFS IDs from all platforms
            all_gtfs_ids = []
            platforms = []
            for stop in group.get("stops", []):
                gtfs_ids = stop.get("gtfsIds", [])
                platform = stop.get("platform", "")
                all_gtfs_ids.extend(gtfs_ids)
                if platform and gtfs_ids:
                    platforms.append(f"  Platform {platform}: {', '.join(gtfs_ids)}")

            matches.append(
                f"Name: {group_name}\n"
                f"All GTFS IDs: {', '.join(all_gtfs_ids)}\n"
                + ("\n".join(platforms) if platforms else "")
            )
            if len(matches) >= limit:
                break

    if not matches:
        return f"No stops found matching '{name}'."

    return "\n\n".join(matches)


@mcp.tool()
async def get_departures(
    stop_ids: str,
    limit: int = 5,
    minutes_after: int = 60,
) -> str:
    """Get upcoming departures from a Prague public transit stop.

    Args:
        stop_ids: GTFS stop ID(s), comma-separated (e.g. "U693Z2P" or "U693Z1P,U693Z2P").
                  Use search_stops to find stop IDs by name.
        limit: Maximum number of departures per stop (default: 5)
        minutes_after: Show departures within this many minutes (default: 60)
    """
    # Split comma-separated IDs into a list for proper URL encoding
    ids_list = [id.strip() for id in stop_ids.split(",")]
    params = {
        "ids": ids_list,
        "limit": limit,
        "minutesAfter": minutes_after,
    }

    try:
        data = await make_golemio_request("/v2/pid/departureboards", params)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"

    if data is None:
        return "Error: GOLEMIO_API_KEY environment variable not set."

    departures = data.get("departures", [])
    if not departures:
        return "No upcoming departures found."

    results = []
    for dep in departures:
        route = dep.get("route", {})
        trip = dep.get("trip", {})
        delay = dep.get("delay", {}).get("minutes", 0)

        departure_time = dep.get("departure_timestamp", {}).get("predicted", "")
        if not departure_time:
            departure_time = dep.get("departure_timestamp", {}).get("scheduled", "N/A")

        delay_str = f" (+{delay} min)" if delay and delay > 0 else ""

        results.append(
            f"{route.get('short_name', '?')} → {trip.get('headsign', 'Unknown')}\n"
            f"Departure: {departure_time}{delay_str}"
        )

    stop_name = data.get("stops", [{}])[0].get("stop_name", "Unknown stop")
    header = f"Departures from {stop_name}:\n" + "=" * 40 + "\n"

    return header + "\n\n".join(results)


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
