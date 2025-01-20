import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID
import logging

from backend.src.db.session import DatabasePool, get_db_pool

logger = logging.getLogger(__name__)
    
router = APIRouter(prefix="/responses", tags=["responses"])

class ResponseCreate(BaseModel):
    request_id: UUID
    status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    response_time_ms: Optional[int]

class Response(BaseModel):
    id: UUID
    request_id: UUID
    status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    response_time_ms: Optional[int]
    created_at: datetime

#TODO: Add authorization so only internal requests can create responses
@router.post("", response_model=Response, status_code=201)
async def create_response(params: ResponseCreate, db_pool: DatabasePool = Depends(get_db_pool)):
    """Create a new response"""
    current_time = datetime.now(tz=timezone.utc)
    response_id = uuid.uuid4()
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
            INSERT INTO responses (id, request_id, status_code, response_body, error_message, response_time_ms, created_at) 
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', response_id, params.request_id, params.status_code, params.response_body, params.error_message, params.response_time_ms, current_time)

            result = await conn.fetchrow('''
                    SELECT * FROM responses WHERE id = $1
                ''', response_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Response with id {response_id} not found "
            )

        logger.info(f"Response created in database: {result}")

        response_data = Response(
            id=result[0],
            request_id=result[1],
            status_code=result[2],
            response_body=result[3],
            error_message=result[4],
            response_time_ms=result[5],
            created_at=result[6]
        )

        return response_data
    
    except Exception as e:
        logger.error(f"Error creating response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create response: {str(e)}")

@router.get("/{response_id}", status_code=200)
async def get_response(response_id: UUID, db_pool: DatabasePool = Depends(get_db_pool)) -> Response:
    """Get response details"""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow('''
                SELECT * FROM responses WHERE id = $1
            ''', response_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Response with id {response_id} not found"
            )

        return Response(
            id=result[0],
            request_id=result[1], 
            status_code=result[2],
            response_body=result[3],
            error_message=result[4],
            response_time_ms=result[5],
            created_at=result[6]
        )

    except Exception as e:
        logger.error(f"Error retrieving response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve response: {str(e)}"
        )

@router.delete("/{response_id}", status_code=204)
async def delete_response(response_id: UUID, db_pool: DatabasePool = Depends(get_db_pool)) -> None:
    """Delete a response"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                DELETE FROM responses WHERE id = $1
            ''', response_id)
        return None
    except Exception as e:
        logger.error(f"Error deleting response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete response: {str(e)}")
    
    