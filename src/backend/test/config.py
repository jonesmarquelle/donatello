import os

TEST_PROXY_URL = "http://localhost:8000"
TEST_PROXY_PORT = 8000

TEST_ENDPOINT_KEY = "test_endpoint_123"
TEST_ENDPOINT_URL = "http://localhost:5001"
TEST_ENDPOINT_PORT = 5001

TEST_KAFKA_TOPIC = 'http_requests'
TEST_KAFKA_GROUP_ID = 'test_group'
TEST_KAFKA_BOOTSTRAP_SERVERS = os.getenv('TEST_KAFKA_BOOTSTRAP_SERVERS')
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
TEST_REDIS_HOST = os.getenv('TEST_REDIS_HOST', 'localhost')
TEST_REDIS_PORT = int(os.getenv('TEST_REDIS_PORT', 6379))

# Logging configuration
LOG_LEVEL = "INFO"