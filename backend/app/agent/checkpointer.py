import logging
import os
import traceback

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

# [v0] Configure logging
logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None
_store: AsyncPostgresStore | None = None


def _get_db_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    logger.info(f"[v0] DATABASE_URL exists: {bool(url)}")
    if url:
        # Mask the password in logs
        masked = url.split("@")[0][:20] + "...@..." if "@" in url else url[:20] + "..."
        logger.info(f"[v0] DATABASE_URL (masked): {masked}")
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def init_persistence() -> None:
    global _pool, _checkpointer, _store

    logger.info("[v0] ===== INIT PERSISTENCE CALLED =====")
    
    db_url = _get_db_url()
    if not db_url:
        logger.error("[v0] DATABASE_URL is not set!")
        raise ValueError("DATABASE_URL environment variable is required")
    
    try:
        logger.info("[v0] Creating connection pool...")
        _pool = AsyncConnectionPool(db_url, max_size=10, open=False)
        await _pool.open()
        logger.info("[v0] Connection pool opened successfully")
    except Exception as e:
        logger.error(f"[v0] Failed to create/open connection pool: {e}")
        logger.error(f"[v0] Traceback: {traceback.format_exc()}")
        raise

    try:
        logger.info("[v0] Setting up checkpointer...")
        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()
        logger.info("[v0] Checkpointer setup complete")
    except Exception as e:
        logger.error(f"[v0] Failed to setup checkpointer: {e}")
        logger.error(f"[v0] Traceback: {traceback.format_exc()}")
        raise

    try:
        logger.info("[v0] Setting up store...")
        _store = AsyncPostgresStore(_pool)
        await _store.setup()
        logger.info("[v0] Store setup complete")
    except Exception as e:
        logger.error(f"[v0] Failed to setup store: {e}")
        logger.error(f"[v0] Traceback: {traceback.format_exc()}")
        raise
    
    logger.info("[v0] ===== PERSISTENCE INIT COMPLETE =====")


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("Persistence not initialized — call init_persistence() first")
    return _checkpointer


def get_store() -> AsyncPostgresStore:
    if _store is None:
        raise RuntimeError("Persistence not initialized — call init_persistence() first")
    return _store
