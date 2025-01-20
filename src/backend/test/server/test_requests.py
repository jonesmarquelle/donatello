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
from backend.src.db.session import DatabasePool, get_db_pool
from backend.src.util.kafka_producer_client import KafkaProducerClient, get_kafka_producer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest_asyncio.fixture(scope="module")
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(requests_router)
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
async def test_create_request(client):
    # Create a job
    job_response = await client.post("/jobs", json={"status": "pending"})
    assert job_response.status_code == 201
    job_data = job_response.json()
    job_id = job_data["id"]

    request_response = await client.post(
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

    assert request_response.status_code == 201
    request_data = request_response.json()

    assert "id" in request_data
    assert request_data["job_id"] == job_id
    assert request_data["status"] == "pending"
    assert "created_at" in request_data
    assert "updated_at" in request_data

@pytest.mark.asyncio
async def test_get_request(client):
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
async def test_get_request_status(client):
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

    # Get the request status
    get_request_status_response = await client.get(f"/requests/{create_request_data['id']}/status")
    assert get_request_status_response.status_code == 200
    get_request_status_data = get_request_status_response.json()

    assert get_request_status_data == create_request_data["status"]

@pytest.mark.asyncio
async def test_update_request_status(client):
    default_status = "pending"
    new_status = "completed"

    # Create a job
    job_response = await client.post("/jobs", json={"status": default_status})
    assert job_response.status_code == 201
    job_data = job_response.json()
    job_id = job_data["id"]

    # Create a request
    create_request_response = await client.post(
        "/requests", 
        json={
            "job_id": job_id, 
            "status": default_status, 
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

    # Update the request status
    update_request_status_response = await client.put(f"/requests/{create_request_data['id']}/status", json={"status": new_status})
    assert update_request_status_response.status_code == 200

    # Get the request status
    get_request_status_response = await client.get(f"/requests/{create_request_data['id']}/status")
    assert get_request_status_response.status_code == 200
    get_request_status_data = get_request_status_response.json()

    assert get_request_status_data == new_status

@pytest.mark.asyncio
async def test_delete_request(client):
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

    # Delete the request
    delete_request_response = await client.delete(f"/requests/{create_request_data['id']}")
    assert delete_request_response.status_code == 204

    # Get the request
    get_request_response = await client.get(f"/requests/{create_request_data['id']}")
    assert get_request_response.status_code == 404
