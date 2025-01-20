import logging
import pytest
import time
import multiprocessing

import requests
from backend.src.util.rate_limited_endpoint import create_app as create_endpoint_app
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

# Create endpoint app with a unique key for testing
TEST_ENDPOINT_KEY = "test_endpoint_123"
endpoint_app = create_endpoint_app(endpoint_key=TEST_ENDPOINT_KEY)

def run_endpoint():
    endpoint_app.run(host='0.0.0.0', port=5001)

@pytest.fixture(scope="module")
def setup_services():
    # Start mock server in a separate process
    endpoint_process = multiprocessing.Process(target=run_endpoint)
    endpoint_process.start()
    
    # Wait for services to start
    time.sleep(2)
    
    yield
    
    # Cleanup
    endpoint_process.terminate()
    endpoint_process.join()

# Test that the endpoint can rate limit requests using Redis
def test_rate_limiting(setup_services):    
    async def run_requests():
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(50):
                tasks.append(
                    session.get(
                        "http://localhost:5001/",
                    )
                )
            responses = await asyncio.gather(*tasks)
            return [r.status for r in responses]
    
    responses = asyncio.run(run_requests())
    
    # Verify that at least one request was rate limited
    assert 429 in responses

# Test that the endpoint can handle different HTTP methods
def test_different_http_methods(setup_services):
    methods = ["GET", "POST", "PUT", "DELETE"]
    for method in methods:
        response = requests.request(method, "http://localhost:5001/")
        assert response.status_code == 200

# Test that the endpoint key is correctly passed through
def test_endpoint_key(setup_services):
    response = requests.get("http://localhost:5001/")
    assert response.json()["endpoint_key"] == TEST_ENDPOINT_KEY

