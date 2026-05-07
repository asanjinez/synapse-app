"""Upload endpoint with docling-powered PDF processing pipeline. (ASA-26)"""
import logging
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks

from app.agent.checkpointer import get_pool
from app.memory.vector import save_chunks

router = APIRouter()
logger = logging.getLogger("synapse.upload")

_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 50


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks = []
    step = _CHUNK_SIZE - _CHUNK_OVERLAP
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + _CHUNK_SIZE])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def _extract_text_docling(file_path: str) -> str:
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(file_path)
        return result.document.export_to_text()
    except ImportError:
        logger.warning("docling not installed — falling back to pypdf")
        return _extract_text_pypdf(file_path)


def _extract_text_pypdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        logger.error("Neither docling nor pypdf available for PDF extraction")
        return ""


async def _process_pdf(source_id: str, file_path: str) -> None:
    pool = get_pool()
    try:
        logger.info("processing PDF source_id=%s", source_id)

        text = _extract_text_docling(file_path)
        if not text.strip():
            logger.warning("empty text extracted from source_id=%s", source_id)
            await _update_source_status(source_id, "error", pool)
            return

        chunks = _chunk_text(text)
        logger.info("source_id=%s → %d chunks", source_id, len(chunks))

        await save_chunks(source_id, chunks, pool)
        await _update_source_status(source_id, "processed", pool)
        logger.info("source_id=%s processing complete", source_id)

    except Exception:
        logger.exception("PDF processing failed for source_id=%s", source_id)
        await _update_source_status(source_id, "error", pool)
    finally:
        try:
            os.unlink(file_path)
        except OSError:
            pass


async def _create_source(user_id: str, filename: str, pool) -> str:
    async with pool.connection() as conn:
        row = await (await conn.execute(
            """
            INSERT INTO sources (user_id, type, name, status)
            VALUES ($1, 'pdf', $2, 'processing')
            RETURNING id
            """,
            user_id, filename,
        )).fetchone()
    return str(row["id"])


async def _update_source_status(source_id: str, status: str, pool) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE sources SET status=$1 WHERE id=$2",
            status, source_id,
        )


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

    source_id = await _create_source(user_id, file.filename, pool)
    background_tasks.add_task(_process_pdf, source_id, tmp_path)

    return {
        "status": "processing",
        "source_id": source_id,
        "filename": file.filename,
        "message": "PDF recibido. Procesando en background — disponible en breve.",
    }
