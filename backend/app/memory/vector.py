"""pgvector RAG search over user materials. (ASA-29)"""
import logging
from litellm import aembedding
from app.config import settings

logger = logging.getLogger("synapse.vector")


async def embed_text(text: str) -> list[float]:
    response = await aembedding(
        model=f"openai/{settings.embedding_model}",
        input=[text],
        api_key=settings.vercel_ai_gateway_key,
        api_base="https://ai-gateway.vercel.sh/v1",
    )
    return response.data[0]["embedding"]


def _vec_to_pg(embedding: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


async def search_user_materials(
    user_id: str, query: str, pool, limit: int = 5
) -> list[str]:
    """Semantic search over source_chunks for a given user."""
    query_embedding = await embed_text(query)
    vec_str = _vec_to_pg(query_embedding)

    async with pool.connection() as conn:
        rows = await (await conn.execute(
            """
            SELECT sc.content, (sc.embedding <=> $1::vector) AS distance
            FROM source_chunks sc
            JOIN sources s ON sc.source_id = s.id
            WHERE s.user_id = $2
            ORDER BY distance ASC
            LIMIT $3
            """,
            vec_str, user_id, limit,
        )).fetchall()

    return [r["content"] for r in rows]


async def save_chunks(source_id: str, chunks: list[str], pool) -> None:
    """Embed and persist text chunks into source_chunks."""
    if not chunks:
        return

    for i, chunk in enumerate(chunks):
        try:
            embedding = await embed_text(chunk)
            vec_str = _vec_to_pg(embedding)
            async with pool.connection() as conn:
                await conn.execute(
                    "INSERT INTO source_chunks (source_id, content, embedding) VALUES ($1, $2, $3::vector)",
                    source_id, chunk, vec_str,
                )
            logger.debug("saved chunk %d/%d for source=%s", i + 1, len(chunks), source_id)
        except Exception:
            logger.exception("failed to embed/save chunk %d for source=%s", i, source_id)
