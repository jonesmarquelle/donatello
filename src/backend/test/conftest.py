from typing import AsyncGenerator
import pytest
import pytest_asyncio
from backend.src.db.session import DatabasePool
from backend.src.util.kafka_consumer_client import KafkaConsumerClient
from backend.src.util.kafka_producer_client import KafkaProducerClient
import json
import os
from dotenv import load_dotenv

load_dotenv()

TEST_KAFKA_TOPIC = 'http_requests'
TEST_KAFKA_GROUP_ID = 'test_group'
TEST_KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

@pytest.fixture
def anyio_backend():
    return 'asyncio'

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