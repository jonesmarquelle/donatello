import os
import logging
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
import uuid
from backend.src.server.jobs.routes import router
from backend.src.db.session import DatabasePool, get_db_pool
from typing import AsyncGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

load_dotenv()
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

@pytest_asyncio.fixture(scope="module")
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app

@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI, db_pool: DatabasePool) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db_pool] = lambda: db_pool
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_job(client):
    """Test creating a new job"""
    response = await client.post("/jobs", json={"status": "pending"})
    
    assert response.status_code == 201
    data = response.json()
    
    assert "id" in data
    assert data["status"] == "pending"
    assert "created_at" in data
    assert "updated_at" in data
    assert data["completed_at"] is None

@pytest.mark.asyncio
async def test_get_job(client):
    """Test retrieving a job"""
    # First create a job
    create_response = await client.post("/jobs", json={"status": "pending"})
    job_id = create_response.json()["id"]
    
    # Then get it
    response = await client.get(f"/jobs/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == job_id
    assert data["status"] == "pending"
    assert "created_at" in data
    assert "updated_at" in data

@pytest.mark.asyncio
async def test_get_nonexistent_job(client):
    """Test retrieving a non-existent job"""
    random_id = str(uuid.uuid4())
    response = await client.get(f"/jobs/{random_id}")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"

@pytest.mark.asyncio
async def test_update_job_status(client):
    """Test updating a job's status"""
    # First create a job
    create_response = await client.post("/jobs", json={"status": "pending"})
    job_id = create_response.json()["id"]
    
    # Update its status
    response = await client.put(f"/jobs/{job_id}/status", params={"job_status": "completed"})
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == job_id
    assert data["status"] == "completed"

@pytest.mark.asyncio
async def test_delete_job(client):
    """Test deleting a job"""
    # First create a job
    create_response = await client.post("/jobs", json={"status": "pending"})
    job_id = create_response.json()["id"]
    
    # Delete it
    response = await client.delete(f"/jobs/{job_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = await client.get(f"/jobs/{job_id}")
    assert get_response.status_code == 404