import logging
import random
from unittest import mock
import uuid
import pytest
from unittest.mock import Mock

from backend.src.worker.worker import RequestWorker
from backend.test.config import *

logger = logging.getLogger(__name__)

TEST_WORKER_KEY = "test_worker_456"
TEST_WORKER_ID = "test_worker"

@pytest.mark.asyncio
async def test_process_request(run_endpoint_server, request_store):
    """Test that worker can successfully make a request to the endpoint"""
    worker = RequestWorker(
        worker_id=TEST_WORKER_ID,
        consumer=None,
        topics=[TEST_KAFKA_TOPIC],
        request_store=request_store
    )    
    # Test request data
    request_data = {
        "method": "post",
        "url": TEST_ENDPOINT_URL,
        "headers": {
            "X-Test-Header": "test",
            "Content-Type": "application/json"
        },
        "body": {"message": f"Response containing {TEST_WORKER_KEY}"}
    }
    
    # Process request
    result = await worker.process_request(request_data)
    
    # Verify response
    assert result["status_code"] == 200
    assert result["worker_id"] == TEST_WORKER_ID
    
    assert TEST_WORKER_KEY in result["body"]

@mock.patch('httpx.AsyncClient.request', autospec=True)
@pytest.mark.asyncio
async def test_worker_dequeue(mock_request, kafka_consumer, kafka_producer, request_store):
    """Test that worker can successfully dequeue a message from Kafka"""

    test_message = {
        'id': str(uuid.uuid4()), 
        'job_id': None, 
        'status': 'pending', 
        'http_request': {
            'method': 'GET', 
            'url': TEST_ENDPOINT_URL, 
            'headers': {"X-Test-Header": "test"},
            'body': f"Response containing {TEST_WORKER_KEY}"
        }, 
        'created_at': '2025-01-20T11:58:02.053901Z', 
        'updated_at': '2025-01-20T11:58:02.053901Z'}

    # Mock the httpx.AsyncClient.request function since we don't care about the actual request
    mock_request.return_value = Mock()
    mock_request.return_value.status_code = 200
    mock_request.return_value.headers = {"X-Test-Header": "test"}
    mock_request.return_value.text = f"Response containing {TEST_WORKER_KEY}"
    
    with kafka_producer as producer:
        producer.publish(test_message)
    
    # Create worker instance
    worker = RequestWorker(
        worker_id=TEST_WORKER_ID,
        consumer=kafka_consumer,
        topics=[TEST_KAFKA_TOPIC],
        request_store=request_store
    )
    
    # Process message from queue
    result = await worker.run(test_mode=True)
    
    # Verify response
    logger.debug(f"DequeuedResult: {result}")
    assert result is not None
    assert result["status_code"] == 200
    assert result["headers"]["X-Test-Header"] == "test"
    assert TEST_WORKER_KEY in result["body"]

@pytest.mark.asyncio
async def test_cleanup_request(kafka_producer, kafka_consumer, request_store):
    """Test that worker can successfully cleanup a request from Redis"""
    request_id = str(random.randint(1, 1000000))
    test_message = {
        'id': request_id, 
        'job_id': None, 
        'status': 'pending', 
        'http_request': {
            'method': 'GET', 
            'url': TEST_ENDPOINT_URL, 
            'headers': {"X-Test-Header": "test"},
            'body': f"Response containing {TEST_WORKER_KEY}"
        }, 
        'created_at': '2025-01-20T11:58:02.053901Z', 
        'updated_at': '2025-01-20T11:58:02.053901Z'}

    # Add request to Redis
    request_store.store_request(request_id, test_message['http_request'])

    #Create Kafka producer
    with kafka_producer as producer:
        producer.publish(test_message)

    # Create worker instance
    worker = RequestWorker(
        worker_id=TEST_WORKER_ID,
        consumer=kafka_consumer,
        topics=[TEST_KAFKA_TOPIC],
        request_store=request_store
    )
    
    # Process message from queue
    result = await worker.run(test_mode=True)
    
    # Verify request was cleaned up from Redis
    assert request_store.get_request(request_id) is None