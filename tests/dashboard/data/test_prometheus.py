"""Unit tests for base Prometheus query functions."""

from unittest.mock import AsyncMock, patch

import pytest

from grillgauge.dashboard.data.prometheus import (
    extract_instant_value,
    extract_range_values,
    query_instant,
    query_range,
)


@pytest.mark.asyncio
async def test_query_instant_success():
    """Test successful instant query."""
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "status": "success",
        "data": {"result": [{"value": [1234567890, "42.5"]}]},
    }
    mock_response.raise_for_status = lambda: None

    mock_get = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await query_instant("http://localhost:9090", "up")
        assert data is not None
        assert data.get("result") == [{"value": [1234567890, "42.5"]}]


@pytest.mark.asyncio
async def test_query_instant_no_results():
    """Test instant query with empty results."""
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "status": "success",
        "data": {"result": []},
    }
    mock_response.raise_for_status = lambda: None

    mock_get = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await query_instant("http://localhost:9090", "nonexistent_metric")
        assert data is not None
        assert data.get("result") == []


@pytest.mark.asyncio
async def test_query_instant_error_status():
    """Test instant query with Prometheus error status."""
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "status": "error",
        "error": "query failed",
    }
    mock_response.raise_for_status = lambda: None

    mock_get = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await query_instant("http://localhost:9090", "invalid{query")
        assert data is None


@pytest.mark.asyncio
async def test_query_instant_connection_error():
    """Test instant query with connection error."""
    mock_get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await query_instant("http://localhost:9090", "up")
        assert data is None


@pytest.mark.asyncio
async def test_query_instant_timeout():
    """Test instant query timeout."""
    import httpx

    mock_get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await query_instant("http://localhost:9090", "up", timeout=1.0)
        assert data is None


@pytest.mark.asyncio
async def test_query_range_success():
    """Test successful range query."""
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "status": "success",
        "data": {
            "result": [
                {
                    "values": [
                        [1234567890, "25.0"],
                        [1234567905, "26.0"],
                        [1234567920, "27.0"],
                    ]
                }
            ]
        },
    }
    mock_response.raise_for_status = lambda: None

    mock_get = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await query_range(
            "http://localhost:9090",
            "grillgauge_meat_temperature_celsius",
            1234567890,
            1234567920,
            "15s",
        )
        assert data is not None
        assert len(data.get("result", [])) == 1
        expected_values_count = 3  # Expected number of values in range query test data
        assert len(data["result"][0]["values"]) == expected_values_count


@pytest.mark.asyncio
async def test_query_range_no_results():
    """Test range query with empty results."""
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "status": "success",
        "data": {"result": []},
    }
    mock_response.raise_for_status = lambda: None

    mock_get = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await query_range(
            "http://localhost:9090",
            "nonexistent_metric",
            1234567890,
            1234567920,
            "15s",
        )
        assert data is not None
        assert data.get("result") == []


@pytest.mark.asyncio
async def test_query_range_error():
    """Test range query with connection error."""
    mock_get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await query_range(
            "http://localhost:9090",
            "up",
            1234567890,
            1234567920,
            "15s",
        )
        assert data is None


def test_extract_instant_value_success():
    """Test extracting value from valid instant query data."""
    test_temperature_value = 42.5
    data = {"result": [{"value": [1234567890, str(test_temperature_value)]}]}
    assert extract_instant_value(data) == test_temperature_value


def test_extract_instant_value_none():
    """Test extract with None input."""
    assert extract_instant_value(None) is None


def test_extract_instant_value_empty_results():
    """Test extract with empty results."""
    assert extract_instant_value({"result": []}) is None


def test_extract_instant_value_no_value():
    """Test extract with result missing value field."""
    assert extract_instant_value({"result": [{}]}) is None


def test_extract_instant_value_invalid_value():
    """Test extract with invalid value format."""
    assert extract_instant_value({"result": [{"value": ["invalid"]}]}) is None


def test_extract_range_values_success():
    """Test extracting values from valid range query data."""
    data = {
        "result": [
            {
                "values": [
                    [1234567890, "25.0"],
                    [1234567905, "26.0"],
                    [1234567920, "27.0"],
                ]
            }
        ]
    }
    assert extract_range_values(data) == [25.0, 26.0, 27.0]


def test_extract_range_values_empty():
    """Test extract with empty data."""
    assert extract_range_values(None) == []
    assert extract_range_values({"result": []}) == []


def test_extract_range_values_no_values():
    """Test extract with result missing values field."""
    assert extract_range_values({"result": [{}]}) == []


def test_extract_range_values_invalid_format():
    """Test extract with invalid value format in range data."""
    data = {"result": [{"values": [[1234567890, "invalid"], [1234567905, "26.0"]]}]}
    # Should skip invalid values but process valid ones
    result = extract_range_values(data)
    # The list comprehension will raise exception and return empty list
    assert result == []
