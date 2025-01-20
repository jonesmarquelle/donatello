import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID

from backend.src.db.session import DatabasePool, get_db_pool

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/jobs", tags=["jobs"])

class JobCreate(BaseModel):
    status: Optional[str] = "pending"

class JobUpdate(BaseModel):
    status: str
    completed_at: Optional[datetime] = None

class Job(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

@router.post("", status_code=201)
async def create_job(job: JobCreate, db_pool: DatabasePool = Depends(get_db_pool)) -> Job:
    """Create a new job"""
    try:
        job_id = str(uuid.uuid4())
        current_time = datetime.now(tz=timezone.utc)

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute('''
                    INSERT INTO jobs (id, status, created_at, updated_at) VALUES ($1, $2, $3, $4)
                ''', job_id, job.status, current_time, current_time)
        
        logger.debug(f"Job created in database: {result}")

        job_data = Job(
            id=job_id,
            status=job.status,
            created_at=current_time,
            updated_at=current_time
        )

        return job_data
    
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@router.get("/{job_id}", status_code=200)
async def get_job(job_id: UUID, db_pool: DatabasePool = Depends(get_db_pool)) -> Job:
    """Get job details"""
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetchrow('''
                    SELECT * FROM jobs WHERE id = $1
                ''', job_id)
        
        logger.debug(f"Job retrieved from database: {result}")

        if not result:
            logger.debug(f"Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        return Job(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")

@router.put("/{job_id}/status", status_code=200)
async def update_job_status(job_id: UUID, job_status: str, db_pool: DatabasePool = Depends(get_db_pool)) -> Job:
    """Update job status"""
    try:
        current_time = datetime.now(tz=timezone.utc)
        
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute('''
                    UPDATE jobs SET status = $1, updated_at = $2 WHERE id = $3
                ''', job_status, current_time, job_id)
        
        logger.debug(f"Job updated in database: {result}")

        job_data = Job(
            id=job_id,
            status=job_status,
            created_at=current_time,
            updated_at=current_time
        )

        return job_data
    except Exception as e:
        logger.error(f"Error updating job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update job: {str(e)}")

@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: UUID, db_pool: DatabasePool = Depends(get_db_pool)) -> None:
    """Delete a job"""
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute('''
                    DELETE FROM jobs WHERE id = $1
                ''', job_id)
        
        logger.debug(f"Job deleted from database: {job_id}")
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")
