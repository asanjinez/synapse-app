import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from app.agent.checkpointer import init_persistence

# [v0] Configure logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[v0] ===== APP LIFESPAN STARTUP =====")
    logger.info("[v0] Checking environment variables...")
    
    env_check = {
        "DATABASE_URL": "set" if os.getenv("DATABASE_URL") else "NOT SET",
        "VERCEL_AI_GATEWAY_KEY": "set" if os.getenv("VERCEL_AI_GATEWAY_KEY") else "NOT SET",
        "MODEL_NAME": os.getenv("MODEL_NAME", "default"),
        "FRONTEND_URL": os.getenv("FRONTEND_URL", "NOT SET"),
        "BACKEND_URL": os.getenv("BACKEND_URL", "NOT SET"),
    }
    logger.info(f"[v0] Environment check: {env_check}")
    
    # Make persistence initialization non-fatal for debugging
    # This allows the app to start even if DB is not configured
    try:
        if os.getenv("DATABASE_URL"):
            logger.info("[v0] Initializing persistence...")
            await init_persistence()
            logger.info("[v0] Persistence initialized successfully")
        else:
            logger.warning("[v0] DATABASE_URL not set - skipping persistence initialization")
            logger.warning("[v0] Chat will fail without database connection")
    except Exception as e:
        logger.error(f"[v0] Failed to initialize persistence: {e}")
        logger.error(f"[v0] Traceback: {traceback.format_exc()}")
        # Don't raise - allow app to start for debugging
        logger.warning("[v0] App will start but chat functionality will be broken")
    
    logger.info("[v0] ===== APP READY =====")
    yield
    logger.info("[v0] ===== APP SHUTDOWN =====")


app = FastAPI(title="Synapse API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(upload_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# [v0] Debug endpoint to check environment and configuration
# With routePrefix "/backend", this will be accessible at /backend/debug
@app.get("/debug")
async def debug():
    """Debug endpoint to check environment configuration. Remove in production."""
    from app.agent.checkpointer import _pool, _checkpointer, _store
    
    return {
        "status": "running",
        "environment": {
            "DATABASE_URL": "set" if os.getenv("DATABASE_URL") else "NOT SET",
            "VERCEL_AI_GATEWAY_KEY": "set" if os.getenv("VERCEL_AI_GATEWAY_KEY") else "NOT SET",
            "MODEL_NAME": os.getenv("MODEL_NAME", "NOT SET"),
            "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL", "NOT SET"),
            "FRONTEND_URL": os.getenv("FRONTEND_URL", "NOT SET"),
        },
        "persistence": {
            "pool": "initialized" if _pool else "NOT initialized",
            "checkpointer": "initialized" if _checkpointer else "NOT initialized",
            "store": "initialized" if _store else "NOT initialized",
        }
    }
