import logging
import random
import uuid
import pytest
import requests
import time
import multiprocessing
from dotenv import load_dotenv
import uvicorn
import json
import httpx
import pytest_asyncio
from backend.src.server.proxy import KAFKA_TOPIC
from backend.test.config import TEST_PROXY_URL, TEST_KAFKA_TOPIC

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Test that the proxy can enqueue a request
@pytest.mark.asyncio
async def test_enqueue_request(run_proxy_server, kafka_consumer):
    # Create a job
    async with httpx.AsyncClient() as client:
        job_response = await client.post(
            f"{TEST_PROXY_URL}/jobs", json={"status": "pending"}
        )
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
    async with httpx.AsyncClient() as client:
        request_response = await client.post(
            f"{TEST_PROXY_URL}/requests", json=test_request
        )

    logger.debug("Create request response: %s", request_response.json())
    # Verify proxy response
    assert request_response.status_code == 201
    request_data = request_response.json()
    request_id = request_data["id"]

    await check_message_in_kafka(
        kafka_consumer,
        request_id,
        test_request["http_request"]["method"],
        test_request["http_request"]["url"],
        test_request["http_request"]["body"],
    )


@pytest.mark.asyncio
async def check_message_in_kafka(
    kafka_consumer, request_id, method, url, body, max_retries=5, timeout_ms=1000
):
    last_message = None
    retry_count: int = 0

    with kafka_consumer as consumer:
        consumer.subscribe([KAFKA_TOPIC])
        while retry_count < max_retries and last_message is None:
            messages = consumer._consumer.poll(
                timeout_ms=timeout_ms
            )  # Poll for messages with 1 second timeout
            for _, partition_messages in messages.items():
                for message in partition_messages:
                    logger.debug(
                        "Message: %s Request ID: %s", message.value, request_id
                    )
                    if message.value["id"] == request_id:
                        last_message = message.value
                        break
            retry_count += 1
            if last_message is None:
                logger.debug(
                    "No message received, attempt %s/%s", retry_count, max_retries
                )

        assert last_message is not None, (
            "No message received after %s attempts" % max_retries
        )

    assert last_message["http_request"]["method"] == method
    assert last_message["http_request"]["url"] == url
    assert last_message["http_request"]["body"] == body
