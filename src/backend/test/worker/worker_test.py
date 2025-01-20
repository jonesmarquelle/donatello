import logging
import os
from unittest import mock
import pytest
import multiprocessing
import time
import requests
from dotenv import load_dotenv
from unittest.mock import Mock

from backend.src.util.rate_limited_endpoint import create_app
from backend.src.worker.worker import RequestWorker

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

#TODO Clean up this env variable hell
TEST_ENDPOINT_KEY = "test_endpoint_123"
TEST_WORKER_KEY = "test_worker_456"
TEST_WORKER_ID = "test_worker"
TEST_KAFKA_TOPIC = os.getenv("TEST_KAFKA_TOPIC", "http_requests")

def test_process_request(setup_services):
    """Test that worker can successfully make a request to the endpoint"""
    worker = RequestWorker(
        worker_id=TEST_WORKER_ID,
        consumer=None,
        topics=[TEST_KAFKA_TOPIC]
    )    
    # Test request data
    request_data = {
        "method": "GET",
        "url": "http://localhost:5001/",
        "headers": {"X-Test-Header": "test"},
        "body": None
    }
    
    # Process request
    result = worker.process_request(request_data)
    
    # Verify response
    print(result)
    assert result["status_code"] == 200
    assert result["worker_id"] == TEST_WORKER_ID
    
    # Verify the response came from our specific endpoint
    response_data = result.get("body")
    assert TEST_ENDPOINT_KEY in response_data

@mock.patch('requests.request', autospec=True)
def test_worker_dequeue(mock_request, kafka_consumer, kafka_producer):
    """Test that worker can successfully dequeue a message from Kafka"""

    test_message = {
        'id': None, 
        'job_id': None, 
        'status': 'pending', 
        'http_request': {
            'method': 'GET', 
            'url': 'http://localhost:5001/', 
            'headers': {"X-Test-Header": "test"},
            'body': f"Response containing {TEST_WORKER_KEY}"
        }, 
        'created_at': '2025-01-20T11:58:02.053901Z', 
        'updated_at': '2025-01-20T11:58:02.053901Z'}

    # Mock the requests.request function
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
        topics=[TEST_KAFKA_TOPIC]
    )
    
    # Process message from queue
    result = worker.run(test_mode=True)
    
    # Verify response
    logger.debug(f"DequeuedResult: {result}")
    assert result is not None
    assert result["status_code"] == 200
    assert result["headers"]["X-Test-Header"] == "test"
    assert TEST_WORKER_KEY in result["body"]

# Create endpoint app with a unique key for testing
def run_endpoint():
    endpoint_app = create_app(endpoint_key=TEST_ENDPOINT_KEY)
    endpoint_app.run(host='0.0.0.0', port=5001)

@pytest.fixture(scope="module")
def setup_services():
    # Start echo endpoint in a separate process
    endpoint_process = multiprocessing.Process(target=run_endpoint)
    endpoint_process.start()
    
    # Wait for service to start
    time.sleep(2)

    try:
        endpoint_health = requests.get("http://localhost:5001/health", timeout=10)
        assert endpoint_health.status_code == 200, "Endpoint not running"
        assert endpoint_health.json()["endpoint_key"] == TEST_ENDPOINT_KEY, "Wrong endpoint responding"
    except Exception as e:
        endpoint_process.terminate()
        raise e
    
    yield
    
    # Cleanup
    endpoint_process.terminate()
    endpoint_process.join()