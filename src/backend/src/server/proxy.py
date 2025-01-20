from typing import List
from fastapi import FastAPI
from dotenv import load_dotenv
from contextlib import AsyncExitStack, asynccontextmanager
import logging
import os

from .jobs.routes import router as jobs_router
from .requests.routes import router as requests_router
from .responses.routes import router as responses_router

from ..db import session as db_pool
from ..db.session import lifespan as db_lifespan

from ..util import kafka_producer_client
from ..util.kafka_producer_client import lifespan as kafka_lifespan

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Load database configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL")
# Load kafka configuration from environment 
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "http_requests")

def app_lifespan(lifespans: List):
    @asynccontextmanager
    async def _lifespan_manager(app: FastAPI):
        exit_stack = AsyncExitStack()
        async with exit_stack:
            for lifespan in lifespans:
                await exit_stack.enter_async_context(lifespan(app))
            yield
            
    return _lifespan_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up proxy service...")
    db_pool.init(app, DATABASE_URL)
    kafka_producer_client.init(app, KAFKA_BOOTSTRAP_SERVERS, topic=KAFKA_TOPIC)
    yield
        
    logger.info("Shutting down proxy service...")

app = FastAPI(
    title="HTTP Queue Proxy",
    description="Service for managing HTTP request queuing and processing",
    version="1.0.0",
    lifespan=app_lifespan([lifespan, db_lifespan, kafka_lifespan])
)

# Include routers
app.include_router(jobs_router)
app.include_router(requests_router)
app.include_router(responses_router)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}