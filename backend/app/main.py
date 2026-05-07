import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from app.agent.checkpointer import init_persistence
from app.workers.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)

_stdout_handler = logging.StreamHandler(sys.stdout)
_stdout_handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
for _name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    _log = logging.getLogger(_name)
    _log.handlers = [_stdout_handler]
    _log.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_persistence()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Synapse API", lifespan=lifespan)

_origins = ["http://localhost:3000"]
if _frontend := os.getenv("FRONTEND_URL", ""):
    _origins.append(_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.vusercontent\.net",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(upload_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
