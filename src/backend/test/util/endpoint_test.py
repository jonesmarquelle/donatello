import logging
import httpx
import pytest
import aiohttp
import asyncio

from backend.test.config import TEST_ENDPOINT_KEY, TEST_ENDPOINT_URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Test that the endpoint can rate limit requests using Redis
def test_rate_limiting(run_endpoint_server):    
    async def run_requests():
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(50):
                tasks.append(
                    session.get(
                        TEST_ENDPOINT_URL,
                    )
                )
            responses = await asyncio.gather(*tasks)
            return [r.status for r in responses]
    
    responses = asyncio.run(run_requests())
    
    # Verify that at least one request was rate limited
    assert 429 in responses

# Test that the endpoint can handle different HTTP methods
@pytest.mark.asyncio
async def test_different_http_methods(run_endpoint_server):
    methods = ["GET", "POST", "PUT", "DELETE"]
    
    for method in methods:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, TEST_ENDPOINT_URL)
            assert response.status_code == 200

# Test that the endpoint key is correctly passed through
@pytest.mark.asyncio
async def test_endpoint_key(run_endpoint_server):
    async with httpx.AsyncClient() as client:
        response = await client.get(TEST_ENDPOINT_URL)
        assert response.json()["endpoint_key"] == TEST_ENDPOINT_KEY

