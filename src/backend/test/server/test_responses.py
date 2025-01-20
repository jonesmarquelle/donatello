import os
import logging
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
import uuid
from typing import AsyncGenerator

from backend.src.server.jobs.routes import router as jobs_router
from backend.src.server.requests.routes import router as requests_router
from backend.src.server.responses.routes import router as responses_router
from backend.src.db.session import DatabasePool, get_db_pool
from backend.src.util.kafka_producer_client import KafkaProducerClient, get_kafka_producer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest_asyncio.fixture(scope="module")
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(requests_router)
    app.include_router(responses_router)
    app.include_router(jobs_router)
    return app

@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI, db_pool: DatabasePool, kafka_producer: KafkaProducerClient) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db_pool] = lambda: db_pool
    app.dependency_overrides[get_kafka_producer] = lambda: kafka_producer
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_response(client):
    # Create a job
    job_response = await client.post("/jobs", json={"status": "pending"})
    assert job_response.status_code == 201
    job_data = job_response.json()
    job_id = job_data["id"]

    # Create a request
    create_request_response = await client.post(
        "/requests", 
        json={
            "job_id": job_id, 
            "status": "pending", 
            "http_request": {
                "method": "GET", 
                "url": "https://example.com", 
                "headers": {}, 
                "body": None
            }
        }
    )
    assert create_request_response.status_code == 201
    create_request_data = create_request_response.json()
    request_id = create_request_data["id"]

    # Create a response
    create_response_response = await client.post(
        "/responses", 
        json={
            "request_id": request_id,
            "status_code": 200,
            "response_body": "Hello, World!",
            "error_message": None,
            "response_time_ms": 100
        }
    )

    assert create_response_response.status_code == 201
    create_response_data = create_response_response.json()

    # Get the response
    get_response_response = await client.get(f"/responses/{create_response_data['id']}")
    assert get_response_response.status_code == 200
    get_response_data = get_response_response.json()

    assert get_response_data["id"] == create_response_data["id"]
    assert get_response_data["request_id"] == request_id
    assert get_response_data["status_code"] == 200
    assert get_response_data["response_body"] == "Hello, World!"
    assert get_response_data["error_message"] is None
    assert get_response_data["response_time_ms"] == 100

@pytest.mark.asyncio
async def test_get_response(client):
   # Create a job
    job_response = await client.post("/jobs", json={"status": "pending"})
    assert job_response.status_code == 201
    job_data = job_response.json()
    job_id = job_data["id"]

    # Create a request
    create_request_response = await client.post(
        "/requests", 
        json={
            "job_id": job_id, 
            "status": "pending", 
            "http_request": {
                "method": "GET", 
                "url": "https://example.com", 
                "headers": {}, 
                "body": None
            }
        }
    )
    assert create_request_response.status_code == 201
    create_request_data = create_request_response.json()

    # Get the request
    get_request_response = await client.get(f"/requests/{create_request_data['id']}")
    assert get_request_response.status_code == 200
    get_request_data = get_request_response.json()

    assert get_request_data["id"] == create_request_data["id"]
    assert get_request_data["job_id"] == create_request_data["job_id"]
    assert get_request_data["status"] == create_request_data["status"]
    assert "created_at" in get_request_data
    assert "updated_at" in get_request_data

@pytest.mark.asyncio
async def test_delete_response(client):
    # Create a job
    job_response = await client.post("/jobs", json={"status": "pending"})
    assert job_response.status_code == 201
    job_data = job_response.json()
    job_id = job_data["id"]

    # Create a request
    create_request_response = await client.post(
        "/requests", 
        json={
            "job_id": job_id, 
            "status": "pending", 
            "http_request": {
                "method": "GET", 
                "url": "https://example.com", 
                "headers": {}, 
                "body": None
            }
        }
    )
    assert create_request_response.status_code == 201
    create_request_data = create_request_response.json()

    # Create a response
    create_response_response = await client.post(
        "/responses", 
        json={
            "request_id": create_request_data["id"],
            "status_code": 200,
            "response_body": "Hello, World!",
            "error_message": None,
            "response_time_ms": 100
        }
    )
    assert create_response_response.status_code == 201
    create_response_data = create_response_response.json()

    # Delete the response
    delete_response_response = await client.delete(f"/responses/{create_response_data['id']}")
    assert delete_response_response.status_code == 204

