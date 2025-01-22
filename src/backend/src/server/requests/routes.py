from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID
import uuid
from backend.src.util.kafka_producer_client import KafkaProducerClient, get_kafka_producer
from backend.src.db.session import get_db_pool, DatabasePool
from backend.src.util.request_store import RequestStore, get_request_store
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requests", tags=["requests"])

class HTTPRequest(BaseModel):
    method: str
    url: str
    headers: dict
    body: Optional[str] = None

class RequestCreate(BaseModel):
    job_id: UUID
    status: Optional[str] = "pending"
    http_request: HTTPRequest

class RequestStatusUpdate(BaseModel):
    status: str

class Request(BaseModel):
    id: UUID
    job_id: UUID
    status: str
    http_request: HTTPRequest
    created_at: datetime
    updated_at: datetime

@router.post("", status_code=201)
async def create_request(
    request: RequestCreate,
    db_pool: DatabasePool = Depends(get_db_pool),
    kafka_producer: KafkaProducerClient = Depends(get_kafka_producer),
    request_store: RequestStore = Depends(get_request_store)
) -> Request:
    """Create a new request"""
    try:
        # Generate new UUID for the request
        request_id = str(uuid.uuid4())
        current_time = datetime.now(tz=timezone.utc)

        async with db_pool.acquire() as conn:
            # First, execute the INSERT
            await conn.execute('''
                INSERT INTO requests (id, job_id, status, created_at, updated_at) 
                VALUES ($1, $2, $3, $4, $5)
            ''', request_id, request.job_id, request.status, current_time, current_time)
            
            # Then, execute the SELECT
            result = await conn.fetchrow('''
                SELECT * FROM requests WHERE id = $1
            ''', request_id)

        logger.info(f"Request created in database: {result}")
        
        # Store HTTP request data in Redis
        request_store.store_request(
            str(request_id),
            jsonable_encoder(request.http_request)
        )
        
        request_data = Request(
            id=result[0],
            job_id=result[1],
            status=result[2],
            http_request=request.http_request,
            created_at=result[3],
            updated_at=result[4]
        )
        
        # Send to Kafka
        with kafka_producer as producer:
            producer.publish(jsonable_encoder(request_data))
        return request_data
            
    except Exception as e:
        logger.error(f"Error creating request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create request: {str(e)}")

@router.get("/{request_id}")
async def get_request(
    request_id: UUID,
    db_pool: DatabasePool = Depends(get_db_pool),
    request_store: RequestStore = Depends(get_request_store)
) -> Request:
    """Get request details"""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                'SELECT * FROM requests WHERE id = $1',
                request_id
            )
            
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Request with id {request_id} not found"
            )
            
        # Retrieve HTTP request data from Redis
        http_request_data = request_store.get_request(str(request_id))
        if http_request_data:
            http_request = HTTPRequest(**http_request_data)
        else:
            # If not found in Redis, return empty request
            http_request = HTTPRequest(
                method="",
                url="",
                headers={},
                body=None
            )
            
        return Request(
            id=result[0],
            job_id=result[1],
            status=result[2],
            http_request=http_request,
            created_at=result[3],
            updated_at=result[4]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve request: {str(e)}"
        )

@router.get("/{request_id}/status")
async def get_request_status(request_id: UUID, db_pool: DatabasePool = Depends(get_db_pool)) -> str:
    """Get request status"""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow('''
                SELECT status FROM requests WHERE id = $1
            ''', request_id)

        if not result:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return result[0]
    except Exception as e:
        logger.error(f"Error retrieving request status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve request status: {str(e)}")

@router.put("/{request_id}/status", status_code=200)
async def update_request_status(request_id: UUID, status_update: RequestStatusUpdate, db_pool: DatabasePool = Depends(get_db_pool)) -> str:
    """Update request status"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE requests SET status = $1 WHERE id = $2
            ''', status_update.status, request_id)
        return status_update.status
    except Exception as e:
        logger.error(f"Error updating request status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update request status: {str(e)}")

@router.delete("/{request_id}", status_code=204)
async def delete_request(
    request_id: UUID,
    db_pool: DatabasePool = Depends(get_db_pool),
    request_store: RequestStore = Depends(get_request_store)
) -> None:
    """Delete a request"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                DELETE FROM requests WHERE id = $1
            ''', request_id)
        # Also delete from Redis
        request_store.delete_request(str(request_id))
        return None
    except Exception as e:
        logger.error(f"Error deleting request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete request: {str(e)}")
