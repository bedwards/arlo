"""Document embedding pipeline using sentence-transformers.

Provides text chunking with overlap, lazy model loading, batch embedding,
and storage to the Chunk table with pgvector embeddings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = structlog.get_logger()

# Module-level lazy singleton for the embedding model.
_model = None


def _get_model(model_name: str = "all-MiniLM-L6-v2"):
    """Lazily load the sentence-transformers model on first use."""
    global _model
    if _model is None:
        log.info("loading_embedding_model", model=model_name)
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(model_name)
        log.info("embedding_model_loaded", model=model_name)
    return _model


def chunk_text(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 200,
) -> list[str]:
    """Split *text* into chunks of roughly *chunk_size* characters with *overlap*.

    The split is character-based (not token-based) for simplicity and speed.
    Each chunk overlaps the previous one by *overlap* characters so that
    context is preserved across chunk boundaries.

    Returns an empty list when the input text is empty or whitespace-only.
    """
    if not text or not text.strip():
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]

        # Only keep non-empty chunks.
        if chunk.strip():
            chunks.append(chunk)

        # Advance by (chunk_size - overlap), ensuring forward progress.
        step = max(chunk_size - overlap, 1)
        start += step

    return chunks


def embed_chunks(
    chunks: list[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 64,
) -> list[list[float]]:
    """Embed a list of text chunks and return 384-dim vectors.

    Uses the sentence-transformers library with batch encoding for efficiency.
    """
    if not chunks:
        return []

    model = _get_model(model_name)
    embeddings = model.encode(
        chunks,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    # Convert numpy arrays to plain Python lists for pgvector compatibility.
    return [vec.tolist() for vec in embeddings]


def store_chunks(
    document_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    session: Session,
) -> int:
    """Persist chunks and their embeddings to the Chunk table.

    Returns the number of chunks stored.
    """
    from arlo.db.models import Chunk

    stored = 0
    for idx, (text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = Chunk(
            document_id=document_id,
            chunk_index=idx,
            text=text,
            embedding=embedding,
            token_count=len(text.split()),  # rough word-count proxy for tokens
        )
        session.add(chunk)
        stored += 1

    session.flush()
    log.info("chunks_stored", document_id=document_id, count=stored)
    return stored
