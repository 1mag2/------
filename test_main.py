import pytest
from fastapi.testclient import TestClient
from main import app
import os
import aiosqlite
from unittest.mock import patch
import httpx

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

# Create a test client with persistent cookies
client = TestClient(app, base_url="http://test")

# Mock response for weather data
MOCK_WEATHER_RESPONSE = {
    "city": "London",
    "country": "GB",
    "current": {
        "temperature_2m": 15.5,
        "relative_humidity_2m": 75,
        "wind_speed_10m": 10.5,
        "weather_code": 1
    },
    "hourly": {
        "time": ["2024-02-20T00:00", "2024-02-20T01:00"],
        "temperature": [15.5, 14.8],
        "weather_code": [1, 2]
    }
}

TEST_DB = "test_weather.db"

@pytest.fixture(autouse=True)
async def setup_test_db():
    # Remove test database if it exists
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Create test database and tables
    async with aiosqlite.connect(TEST_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    
    # Override the database path in main.py
    app.state.db_path = TEST_DB
    
    yield
    
    # Cleanup after tests
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

@pytest.fixture
async def test_client():
    # Create a new client for each test
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

async def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Weather Forecast" in response.text

@patch('main.get_weather_data')
async def test_search_valid_city(mock_get_weather):
    mock_get_weather.return_value = MOCK_WEATHER_RESPONSE
    response = client.post("/search", data={"city": "London"})
    assert response.status_code == 200
    data = response.json()
    assert data == MOCK_WEATHER_RESPONSE

@patch('main.get_weather_data')
async def test_search_invalid_city(mock_get_weather):
    mock_get_weather.return_value = None
    response = client.post("/search", data={"city": "NonExistentCity12345"})
    assert response.status_code == 404
    assert "error" in response.json()

async def test_autocomplete():
    response = client.get("/cities/autocomplete?q=Lon")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("name" in city for city in data)

async def test_autocomplete_short_query():
    response = client.get("/cities/autocomplete?q=L")
    assert response.status_code == 200
    assert response.json() == []

@patch('main.get_weather_data')
async def test_stats(mock_get_weather):
    mock_get_weather.return_value = MOCK_WEATHER_RESPONSE
    
    # Create a new client with cookies
    test_client = TestClient(app, base_url="http://test")
    test_client.cookies.set("user_id", "test_user")
    
    # Add test data
    test_cities = ["London", "Paris", "London", "New York"]
    
    for city in test_cities:
        response = test_client.post("/search", data={"city": city})
        assert response.status_code == 200
    
    # Check stats
    response = test_client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    
