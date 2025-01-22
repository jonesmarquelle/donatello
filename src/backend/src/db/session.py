from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncpg
from fastapi import FastAPI, Request

class DatabasePool:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool = None

    async def create_pool(self):
        if not self._pool:
            self._pool = await asyncpg.create_pool(self.dsn)
        return self._pool

    async def close_pool(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        if not self._pool:
            await self.create_pool()
        async with self._pool.acquire() as connection:
            yield connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    await app.state.db_pool.create_pool()
    yield
    await app.state.db_pool.close_pool()

def init(app: FastAPI, db_url: str) -> None:
    """Initialize database connection pool"""
    app.state.db_pool = DatabasePool(db_url)

async def get_db_pool(request: Request) -> DatabasePool:
    """Dependency to get database pool"""
    if not hasattr(request.app.state, "db_pool"):
        raise RuntimeError("Database pool not initialized. Ensure init_db() is called during app startup.")
    return request.app.state.db_pool