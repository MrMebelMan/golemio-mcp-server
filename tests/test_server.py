"""Unit tests for Golemio MCP Server."""

import pytest
import respx
from httpx import Response

from golemio_mcp import server as golemio_server


@pytest.fixture
def mock_api_key(monkeypatch):
    """Set up mock API key for tests."""
    monkeypatch.setenv("GOLEMIO_API_KEY", "test-api-key")


@pytest.fixture
def no_api_key(monkeypatch):
    """Ensure no API key is set."""
    monkeypatch.delenv("GOLEMIO_API_KEY", raising=False)


# Sample GeoJSON response data
SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
            "properties": {"id": "test-1", "name": "Test Location"},
        }
    ],
}


class TestMakeGolemioRequest:
    """Tests for the make_golemio_request helper function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful API request."""
        respx.get("https://api.golemio.cz/v2/test/").mock(
            return_value=Response(200, json={"data": "test"})
        )

        result = await golemio_server.make_golemio_request("/v2/test/")

        assert result == {"data": "test"}
        assert respx.calls.last.request.headers["X-Access-Token"] == "test-api-key"
        assert respx.calls.last.request.headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    @respx.mock
    async def test_with_params(self, mock_api_key):
        """Test API request with query parameters."""
        respx.get("https://api.golemio.cz/v2/test/").mock(
            return_value=Response(200, json={"data": "test"})
        )

        await golemio_server.make_golemio_request(
            "/v2/test/", {"limit": 10, "offset": 0, "unused": None}
        )

        # Check that None values are filtered out
        assert "limit=10" in str(respx.calls.last.request.url)
        assert "offset=0" in str(respx.calls.last.request.url)
        assert "unused" not in str(respx.calls.last.request.url)

    @pytest.mark.asyncio
    async def test_missing_api_key(self, no_api_key):
        """Test that missing API key returns None."""
        result = await golemio_server.make_golemio_request("/v2/test/")
        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error(self, mock_api_key):
        """Test HTTP error handling."""
        respx.get("https://api.golemio.cz/v2/test/").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        with pytest.raises(Exception):
            await golemio_server.make_golemio_request("/v2/test/")


class TestGetBicycleCounters:
    """Tests for get_bicycle_counters tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful bicycle counters retrieval."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
                    "properties": {
                        "id": "counter-1",
                        "name": "Test Counter",
                        "directions": "Both",
                    },
                }
            ],
        }
        respx.get("https://api.golemio.cz/v2/bicyclecounters/").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_bicycle_counters()

        assert "Test Counter" in result
        assert "counter-1" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_with_location_params(self, mock_api_key):
        """Test bicycle counters with location parameters."""
        respx.get("https://api.golemio.cz/v2/bicyclecounters/").mock(
            return_value=Response(200, json=SAMPLE_GEOJSON)
        )

        await golemio_server.get_bicycle_counters(
            latlng="50.0890,14.4168", range=1000, limit=5
        )

        url = str(respx.calls.last.request.url)
        assert "latlng=50.0890%2C14.4168" in url
        assert "range=1000" in url
        assert "limit=5" in url

    @pytest.mark.asyncio
    async def test_missing_api_key(self, no_api_key):
        """Test error message when API key is missing."""
        result = await golemio_server.get_bicycle_counters()
        assert "GOLEMIO_API_KEY" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_results(self, mock_api_key):
        """Test handling of empty results."""
        respx.get("https://api.golemio.cz/v2/bicyclecounters/").mock(
            return_value=Response(200, json={"type": "FeatureCollection", "features": []})
        )

        result = await golemio_server.get_bicycle_counters()
        assert "No results found" in result


class TestGetBicycleDetections:
    """Tests for get_bicycle_detections tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful bicycle detections retrieval."""
        response_data = [
            {"measured_from": "2024-01-01T00:00:00Z", "value": 42},
            {"measured_from": "2024-01-01T01:00:00Z", "value": 35},
        ]
        respx.get("https://api.golemio.cz/v2/bicyclecounters/detections").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_bicycle_detections(
            id="counter-1", from_date="2024-01-01T00:00:00Z"
        )

        assert "42" in result
        assert "2024-01-01" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_with_date_params(self, mock_api_key):
        """Test detections with date parameters."""
        respx.get("https://api.golemio.cz/v2/bicyclecounters/detections").mock(
            return_value=Response(200, json=[])
        )

        await golemio_server.get_bicycle_detections(
            id="counter-1",
            from_date="2024-01-01T00:00:00Z",
            to_date="2024-01-31T23:59:59Z",
        )

        url = str(respx.calls.last.request.url)
        assert "id=counter-1" in url
        assert "from=" in url
        assert "to=" in url


class TestGetAirQualityStations:
    """Tests for get_air_quality_stations tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful air quality stations retrieval."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
                    "properties": {
                        "id": "aq-1",
                        "name": "Air Quality Station 1",
                        "district": "Praha 1",
                        "measurement": {
                            "components": [
                                {"type": "PM10", "value": 25, "aqi_level": "good"}
                            ]
                        },
                    },
                }
            ],
        }
        respx.get("https://api.golemio.cz/v2/airqualitystations/").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_air_quality_stations()

        assert "Air Quality Station 1" in result
        assert "PM10" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_with_districts(self, mock_api_key):
        """Test filtering by districts."""
        respx.get("https://api.golemio.cz/v2/airqualitystations/").mock(
            return_value=Response(200, json=SAMPLE_GEOJSON)
        )

        await golemio_server.get_air_quality_stations(districts="praha-1,praha-2")

        url = str(respx.calls.last.request.url)
        assert "districts=" in url


class TestGetWasteStations:
    """Tests for get_waste_stations tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful waste stations retrieval."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
                    "properties": {
                        "id": "waste-1",
                        "name": "Waste Station 1",
                        "address": {"address_formatted": "Test Street 123"},
                        "containers": [
                            {
                                "trash_type": {"description": "Paper"},
                                "occupancy": {"percent": 75},
                            }
                        ],
                    },
                }
            ],
        }
        respx.get("https://api.golemio.cz/v2/sortedwastestations").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_waste_stations()

        assert "Waste Station 1" in result
        assert "Paper" in result
        assert "75%" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_only_monitored(self, mock_api_key):
        """Test filtering to only monitored stations."""
        respx.get("https://api.golemio.cz/v2/sortedwastestations").mock(
            return_value=Response(200, json=SAMPLE_GEOJSON)
        )

        await golemio_server.get_waste_stations(onlyMonitored=True)

        url = str(respx.calls.last.request.url)
        assert "onlymonitored=true" in url.lower()


class TestGetParkingLots:
    """Tests for get_parking_lots tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful parking lots retrieval using v1 API."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
                    "properties": {
                        "id": "parking-1",
                        "name": "City Parking",
                        "parking_type": {"description": "Underground"},
                        "total_num_of_places": 200,
                        "num_of_free_places": 50,
                    },
                }
            ],
        }
        # Note: Parking uses v1 API
        respx.get("https://api.golemio.cz/v1/parkings/").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_parking_lots()

        assert "City Parking" in result
        assert "50 free / 200 total" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_uses_v1_api(self, mock_api_key):
        """Verify that parking uses v1 API endpoint."""
        respx.get("https://api.golemio.cz/v1/parkings/").mock(
            return_value=Response(200, json=SAMPLE_GEOJSON)
        )

        await golemio_server.get_parking_lots()

        assert "/v1/parkings/" in str(respx.calls.last.request.url)


class TestGetCityDistricts:
    """Tests for get_city_districts tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful city districts retrieval."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [[]]},
                    "properties": {
                        "id": "district-1",
                        "name": "Praha 1",
                        "slug": "praha-1",
                    },
                }
            ],
        }
        respx.get("https://api.golemio.cz/v2/citydistricts/").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_city_districts()

        assert "Praha 1" in result
        assert "praha-1" in result


class TestGetMedicalInstitutions:
    """Tests for get_medical_institutions tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful medical institutions retrieval."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
                    "properties": {
                        "id": "med-1",
                        "name": "City Hospital",
                        "type": "Hospital",
                        "address": {"address_formatted": "Medical Street 1"},
                        "telephone": "+420123456789",
                        "email": "info@hospital.cz",
                    },
                }
            ],
        }
        respx.get("https://api.golemio.cz/v2/medicalinstitutions/").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_medical_institutions()

        assert "City Hospital" in result
        assert "Hospital" in result


class TestGetMunicipalLibraries:
    """Tests for get_municipal_libraries tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful municipal libraries retrieval."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
                    "properties": {
                        "id": "lib-1",
                        "name": "Central Library",
                        "address": {"address_formatted": "Book Street 1"},
                        "telephone": "+420987654321",
                        "email": "info@library.cz",
                        "web": {"url": "https://library.cz"},
                    },
                }
            ],
        }
        respx.get("https://api.golemio.cz/v2/municipallibraries/").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_municipal_libraries()

        assert "Central Library" in result
        assert "library.cz" in result


class TestGetPlaygrounds:
    """Tests for get_playgrounds tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful playgrounds retrieval."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
                    "properties": {
                        "id": "play-1",
                        "name": "Fun Playground",
                        "type": "Children",
                        "district": "Praha 2",
                        "address": {"address_formatted": "Park Street 1"},
                    },
                }
            ],
        }
        respx.get("https://api.golemio.cz/v2/playgrounds/").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_playgrounds()

        assert "Fun Playground" in result
        assert "Children" in result


class TestGetGardens:
    """Tests for get_gardens tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful gardens retrieval."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [14.4168, 50.0890]},
                    "properties": {
                        "id": "garden-1",
                        "name": "Royal Garden",
                        "type": "Historic",
                        "description": "Beautiful historic garden",
                        "district": "Praha 1",
                    },
                }
            ],
        }
        respx.get("https://api.golemio.cz/v2/gardens/").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_gardens()

        assert "Royal Garden" in result
        assert "Historic" in result
        assert "Beautiful historic garden" in result


class TestSearchStops:
    """Tests for search_stops tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self):
        """Test successful stop search."""
        response_data = {
            "stopGroups": [
                {
                    "name": "Avia Letňany",
                    "stops": [
                        {"platform": "A", "gtfsIds": ["U1234Z1P"]},
                        {"platform": "B", "gtfsIds": ["U1234Z2P"]},
                    ],
                },
                {
                    "name": "Letňany",
                    "stops": [{"platform": "1", "gtfsIds": ["U5678Z1P"]}],
                },
            ]
        }
        respx.get("https://data.pid.cz/stops/json/stops.json").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.search_stops("Letňany")

        assert "Avia Letňany" in result
        assert "U1234Z1P" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_matches(self):
        """Test search with no matches."""
        response_data = {
            "stopGroups": [
                {"name": "Muzeum", "stops": [{"gtfsIds": ["U123"]}]}
            ]
        }
        respx.get("https://data.pid.cz/stops/json/stops.json").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.search_stops("Nonexistent")

        assert "No stops found" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_limit(self):
        """Test search result limit."""
        response_data = {
            "stopGroups": [
                {"name": f"Stop {i}", "stops": [{"gtfsIds": [f"U{i}"]}]}
                for i in range(20)
            ]
        }
        respx.get("https://data.pid.cz/stops/json/stops.json").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.search_stops("Stop", limit=3)

        # Should only have 3 results
        assert result.count("All GTFS IDs:") == 3


class TestGetDepartures:
    """Tests for get_departures tool."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, mock_api_key):
        """Test successful departures retrieval."""
        response_data = {
            "stops": [{"stop_name": "Avia Letňany"}],
            "departures": [
                {
                    "route": {"short_name": "195"},
                    "trip": {"headsign": "Florenc"},
                    "delay": {"minutes": 2},
                    "departure_timestamp": {
                        "predicted": "2024-01-15T10:30:00",
                        "scheduled": "2024-01-15T10:28:00",
                    },
                },
                {
                    "route": {"short_name": "C"},
                    "trip": {"headsign": "Háje"},
                    "delay": {"minutes": 0},
                    "departure_timestamp": {
                        "predicted": "2024-01-15T10:35:00",
                        "scheduled": "2024-01-15T10:35:00",
                    },
                },
            ],
        }
        respx.get("https://api.golemio.cz/v2/pid/departureboards").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_departures("U1234Z1P")

        assert "Avia Letňany" in result
        assert "195" in result
        assert "Florenc" in result
        assert "+2 min" in result
        assert "C" in result
        assert "Háje" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_departures(self, mock_api_key):
        """Test with no departures."""
        response_data = {"stops": [], "departures": []}
        respx.get("https://api.golemio.cz/v2/pid/departureboards").mock(
            return_value=Response(200, json=response_data)
        )

        result = await golemio_server.get_departures("U1234Z1P")

        assert "No upcoming departures" in result

    @pytest.mark.asyncio
    async def test_missing_api_key(self, no_api_key):
        """Test error message when API key is missing."""
        result = await golemio_server.get_departures("U1234Z1P")
        assert "GOLEMIO_API_KEY" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_params_passed(self, mock_api_key):
        """Test that parameters are passed correctly."""
        respx.get("https://api.golemio.cz/v2/pid/departureboards").mock(
            return_value=Response(200, json={"stops": [], "departures": []})
        )

        await golemio_server.get_departures("U1234Z1P,U5678Z2P", limit=10, minutes_after=120)

        url = str(respx.calls.last.request.url)
        assert "ids=U1234Z1P" in url
        assert "limit=10" in url
        assert "minutesAfter=120" in url


class TestHttpErrors:
    """Tests for HTTP error handling across all tools."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_unauthorized_error(self, mock_api_key):
        """Test 401 error handling."""
        respx.get("https://api.golemio.cz/v2/bicyclecounters/").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        result = await golemio_server.get_bicycle_counters()
        assert "API error: 401" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error(self, mock_api_key):
        """Test 500 error handling."""
        respx.get("https://api.golemio.cz/v2/gardens/").mock(
            return_value=Response(500, json={"error": "Internal Server Error"})
        )

        result = await golemio_server.get_gardens()
        assert "API error: 500" in result
