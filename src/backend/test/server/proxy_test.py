import logging
import random
import uuid
import pytest
import requests
import time
import multiprocessing
from dotenv import load_dotenv
from backend.src.server.proxy import app
import uvicorn
import json

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

KAFKA_TOPIC = "http_requests"

def run_proxy():
    uvicorn.run(app, host='0.0.0.0', port=8000)

@pytest.fixture(scope="module")
def setup_services():
    # Start proxy in a separate process
    proxy_process = multiprocessing.Process(target=run_proxy)
    proxy_process.start()
    
    # Wait for services to start
    time.sleep(2)
    
    # Verify both services are running
    try:
        proxy_health = requests.get("http://localhost:8000/health", timeout=10)
        assert proxy_health.status_code == 200, "Proxy not running"
    except Exception as e:
        proxy_process.terminate()
        raise e
    
    yield
    
    # Cleanup
    proxy_process.terminate()
    proxy_process.join()

# Test that the proxy can enqueue a request
def test_enqueue_request(setup_services, kafka_consumer):
    # Create a job
    job_response = requests.post("http://localhost:8000/jobs", json={"status": "pending"})
    logger.debug("Create job response: %s", job_response.json())
    job_id = job_response.json()["id"]

    # Test data
    test_request = {
        "http_request": {
            "method": "POST",
            "url": "http://localhost:5000/",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"test": str(random.randint(1, 1000000))}),
        },
        "job_id": job_id,
    }
    
    # Send request to proxy
    request_response = requests.post(
        "http://localhost:8000/requests",
        json=test_request
    )
    
    logger.debug("Create request response: %s", request_response.json())
    # Verify proxy response
    assert request_response.status_code == 201
    request_data = request_response.json()
    request_id = request_data["id"]
    
    check_message_in_kafka(
        kafka_consumer, 
        request_id,
        test_request["http_request"]["method"],
        test_request["http_request"]["url"],
        test_request["http_request"]["body"]
    )

def check_message_in_kafka(kafka_consumer, request_id, method, url, body, max_retries=5, timeout_ms=1000):
     # Verify message was published to Kafka
    last_message = None
    retry_count: int = 0
    
    with kafka_consumer as consumer:
        consumer.subscribe([KAFKA_TOPIC])
        while retry_count < max_retries and last_message is None:
            messages = consumer._consumer.poll(timeout_ms=timeout_ms)  # Poll for messages with 1 second timeout
            for _, partition_messages in messages.items():
                for message in partition_messages:
                    logger.debug("Message: %s Request ID: %s", message.value, request_id)
                    if message.value["id"] == request_id:
                        last_message = message.value
                        break
            retry_count += 1
            if last_message is None:
                logger.debug("No message received, attempt %s/%s", retry_count, max_retries)
        
        assert last_message is not None, "No message received after %s attempts" % max_retries
    
    assert last_message["http_request"]["method"] == method
    assert last_message["http_request"]["url"] == url
    assert last_message["http_request"]["body"] == body
