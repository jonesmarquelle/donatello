import logging
import multiprocessing
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from backend.src.db.session import DatabasePool
from backend.src.util.kafka_consumer_client import KafkaConsumerClient
from backend.src.util.kafka_producer_client import KafkaProducerClient
from backend.src.util.rate_limiter import RateLimiter
from backend.src.util.request_store import RequestStore
import json
from backend.src.server.proxy import app
import uvicorn
import httpx
import time
from backend.src.util.rate_limited_endpoint import create_app as create_endpoint_app
from backend.test.config import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest.fixture
def anyio_backend():
    return 'asyncio'

# Create endpoint app with a unique key for testing
def run_endpoint():
    rate_limiter = RateLimiter(
        redis_host=TEST_REDIS_HOST,
        redis_port=TEST_REDIS_PORT
    )
    rate_limiter.reset()

    endpoint_app = create_endpoint_app(endpoint_key=TEST_ENDPOINT_KEY, rate_limiter=rate_limiter)
    # Store rate_limiter as a global variable on the Flask app
    endpoint_app.rate_limiter = rate_limiter
    endpoint_app.run(host='0.0.0.0', port=TEST_ENDPOINT_PORT)

@pytest_asyncio.fixture(scope="function")
async def run_endpoint_server():
    # Start echo endpoint in a separate process
    endpoint_process = multiprocessing.Process(target=run_endpoint)
    endpoint_process.start()
    
    # Wait for service to start
    time.sleep(2)

    try:
        async with httpx.AsyncClient() as client:
            endpoint_health = await client.get(f"{TEST_ENDPOINT_URL}/health", timeout=10)
            assert endpoint_health.status_code == 200, "Endpoint not running"
            assert endpoint_health.json()["endpoint_key"] == TEST_ENDPOINT_KEY, "Wrong endpoint responding"
    except Exception as e:
        endpoint_process.terminate()
        raise e
    
    yield
    
    # Cleanup
    endpoint_process.terminate()
    endpoint_process.join()

def run_proxy():
    uvicorn.run(app, host='0.0.0.0', port=TEST_PROXY_PORT)

@pytest.fixture(scope="module")
def run_proxy_server():
    proxy_process = multiprocessing.Process(
        target=run_proxy
    )
    proxy_process.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Verify server is running
    try:
        response = httpx.get(f"{TEST_PROXY_URL}/health")
        assert response.status_code == 200, "Proxy server not running"
    except Exception as e:
        proxy_process.terminate()
        raise e
    
    yield
    proxy_process.terminate()
    proxy_process.join()

@pytest_asyncio.fixture(scope="function")
async def db_pool() -> AsyncGenerator[DatabasePool, None]:
    pool = DatabasePool(TEST_DB_URL)
    yield pool
    await pool.close_pool()

@pytest.fixture
def kafka_producer():
    producer = KafkaProducerClient(
        bootstrap_servers=TEST_KAFKA_BOOTSTRAP_SERVERS,
        topic=TEST_KAFKA_TOPIC,
    )
    producer.clear_topic()
    yield producer
    producer.close()

@pytest.fixture()
def kafka_consumer():
    consumer = KafkaConsumerClient(
        bootstrap_servers=TEST_KAFKA_BOOTSTRAP_SERVERS,
        group_id=TEST_KAFKA_GROUP_ID,
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        consumer_timeout_ms=1000
    )
    yield consumer
    consumer.close()

@pytest.fixture()
def request_store():
    store = RequestStore(
        redis_host=TEST_REDIS_HOST,
        redis_port=TEST_REDIS_PORT
    )
    yield store
    # Clean up any test data and close connection
    test_keys = store.redis.keys("request:*")
    if test_keys:
        store.redis.delete(*test_keys)
    store.close()