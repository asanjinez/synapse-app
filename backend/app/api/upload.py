"""Upload endpoint — legacy/internal. Primary flow is via chat with Vercel Blob. (ASA-26)"""
import logging
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks

from app.agent.checkpointer import get_pool
from app.memory.vector import save_chunks
from app.memory.pdf import extract_text_docling, chunk_text, create_source, update_source_status

router = APIRouter()
logger = logging.getLogger("synapse.upload")


async def _process_pdf(source_id: str, file_path: str) -> None:
    pool = get_pool()
    try:
        logger.info("processing PDF source_id=%s", source_id)
        text = extract_text_docling(file_path)
        if not text.strip():
            logger.warning("empty text extracted from source_id=%s", source_id)
            await update_source_status(source_id, "error", pool)
            return

        chunks = chunk_text(text)
        logger.info("source_id=%s → %d chunks", source_id, len(chunks))
        await save_chunks(source_id, chunks, pool)
        await update_source_status(source_id, "processed", pool)
        logger.info("source_id=%s processing complete", source_id)

    except Exception:
        logger.exception("PDF processing failed for source_id=%s", source_id)
        await update_source_status(source_id, "error", pool)
    finally:
        try:
            os.unlink(file_path)
        except OSError:
            pass


@router.post("/api/upload")
async def upload(
    background_tasks: BackgroundTasks,
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pool = get_pool()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    source_id = await create_source(user_id, file.filename, pool)
    background_tasks.add_task(_process_pdf, source_id, tmp_path)

    return {
        "status": "processing",
        "source_id": source_id,
        "filename": file.filename,
        "message": "PDF recibido. Procesando en background.",
    }
