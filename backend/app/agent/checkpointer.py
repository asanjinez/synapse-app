import os
import logging
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

logger = logging.getLogger("synapse.checkpointer")

_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None
_store: AsyncPostgresStore | None = None


def _get_db_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def init_persistence() -> None:
    global _pool, _checkpointer, _store

    db_url = _get_db_url()
    logger.info("opening connection pool")
    _pool = AsyncConnectionPool(
        db_url,
        max_size=10,
        open=False,
        kwargs={"autocommit": True},
    )
    await _pool.open()
    logger.info("pool open — setting up checkpointer")

    _checkpointer = AsyncPostgresSaver(_pool)
    await _checkpointer.setup()
    logger.info("checkpointer ready")

    _store = AsyncPostgresStore(_pool)
    await _store.setup()
    logger.info("store ready — persistence initialized")


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("Persistence not initialized — call init_persistence() first")
    return _checkpointer


def get_store() -> AsyncPostgresStore:
    if _store is None:
        raise RuntimeError("Persistence not initialized — call init_persistence() first")
    return _store


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Persistence not initialized — call init_persistence() first")
    return _pool
