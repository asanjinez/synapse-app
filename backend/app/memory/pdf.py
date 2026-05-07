"""PDF text extraction and source management shared across upload and chat flows."""
import logging
import os
import tempfile

import httpx

logger = logging.getLogger("synapse.pdf")


def extract_text_docling(file_path: str) -> str:
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(file_path)
        return result.document.export_to_text()
    except ImportError:
        logger.warning("docling not installed — falling back to pypdf")
        return extract_text_pypdf(file_path)


def extract_text_pypdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        logger.error("Neither docling nor pypdf available for PDF extraction")
        return ""


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


async def download_from_blob(blob_url: str) -> str:
    """Download a public Vercel Blob file to a temp file. Returns the temp file path."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            blob_url,
            follow_redirects=True,
            timeout=60.0,
        )
        resp.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


async def create_source(user_id: str, filename: str, pool) -> str:
    async with pool.connection() as conn:
        row = await (await conn.execute(
            """
            INSERT INTO sources (user_id, type, name, status)
            VALUES (%s, 'pdf', %s, 'processing')
            RETURNING id
            """,
            (user_id, filename),
        )).fetchone()
    return str(row["id"])


async def update_source_status(source_id: str, status: str, pool) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE sources SET status=%s WHERE id=%s",
            (status, source_id),
        )
