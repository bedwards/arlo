"""Main ingestion pipeline orchestrator.

Implements a source-registry pattern so each source type (news, youtube,
substack, markets, economic) can register a handler.  The ``run`` method
drives the full cycle: fetch content -> parse -> chunk -> embed -> store.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import structlog

log = structlog.get_logger()

# Type alias for a source handler function.
# Signature: (session, sources_config) -> list[int]  (returns new document IDs)
SourceHandler = Callable


class IngestionPipeline:
    """Registry-based ingestion pipeline.

    Usage::

        pipeline = IngestionPipeline()
        pipeline.register("news", news_handler)
        pipeline.run("news")  # fetch -> chunk -> embed -> store
    """

    def __init__(self) -> None:
        self._handlers: dict[str, SourceHandler] = {}

    # ----- registry -----

    def register(self, source_type: str, handler: SourceHandler) -> None:
        """Register a handler for *source_type*."""
        self._handlers[source_type] = handler
        log.debug("handler_registered", source_type=source_type)

    @property
    def registered_types(self) -> list[str]:
        return list(self._handlers.keys())

    # ----- main entry point -----

    def run(self, source_type: str) -> None:
        """Execute the full ingestion cycle for *source_type*.

        1. Look up the registered handler.
        2. Load sources.toml for feed URLs / config.
        3. Call the handler to fetch & store Documents (handler manages dedup).
        4. Chunk and embed all newly created Documents.
        5. Commit the session.
        """
        if source_type not in self._handlers:
            available = ", ".join(self._handlers) or "(none)"
            raise ValueError(
                f"No handler registered for source type {source_type!r}. "
                f"Available: {available}"
            )

        from arlo.config import get_config
        from arlo.db.postgres import get_session

        config = get_config()
        session = get_session()

        log.info("pipeline_start", source_type=source_type)

        try:
            # Step 1 — Load sources configuration.
            sources_config = _load_sources_toml()

            # Step 2 — Run the source handler (fetch, parse, store Documents).
            handler = self._handlers[source_type]
            new_doc_ids = handler(session, sources_config)

            if not new_doc_ids:
                log.info("pipeline_no_new_documents", source_type=source_type)
                session.commit()
                return

            log.info("pipeline_documents_created", source_type=source_type, count=len(new_doc_ids))

            # Step 3 — Chunk and embed each new document.
            from arlo.db.models import Document
            from arlo.ingest.embedder import chunk_text, embed_chunks, store_chunks

            ingest_cfg = config.ingest
            total_chunks = 0

            for doc_id in new_doc_ids:
                try:
                    doc = session.get(Document, doc_id)
                    if doc is None or not doc.full_text:
                        log.warning("skipping_empty_document", doc_id=doc_id)
                        continue

                    chunks = chunk_text(
                        doc.full_text,
                        chunk_size=ingest_cfg.chunk_size,
                        overlap=ingest_cfg.chunk_overlap,
                    )
                    if not chunks:
                        continue

                    embeddings = embed_chunks(chunks, model_name=ingest_cfg.embedding_model)
                    stored = store_chunks(doc_id, chunks, embeddings, session)
                    total_chunks += stored

                except Exception:
                    log.exception("chunk_embed_error", doc_id=doc_id)
                    # Continue with remaining documents.
                    continue

            session.commit()
            log.info(
                "pipeline_complete",
                source_type=source_type,
                documents=len(new_doc_ids),
                chunks=total_chunks,
            )

        except Exception:
            session.rollback()
            log.exception("pipeline_error", source_type=source_type)
            raise
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Sources TOML loading
# ---------------------------------------------------------------------------

def _load_sources_toml() -> dict:
    """Load config/sources.toml, returning an empty dict if not found."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    toml_path = Path("config/sources.toml")
    if not toml_path.exists():
        log.warning("sources_toml_not_found", path=str(toml_path))
        return {}

    with open(toml_path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Built-in news handler
# ---------------------------------------------------------------------------

def _news_handler(session, sources_config: dict) -> list[int]:
    """Handler for source_type='news'.

    Reads RSS feed entries from sources.toml ``[rss]`` section and ingests
    each feed via the news module.
    """
    from arlo.ingest.news import ingest_feed

    rss_section = sources_config.get("rss", {})
    feeds = rss_section.get("feeds", [])

    if not feeds:
        log.warning("no_rss_feeds_configured")
        return []

    all_doc_ids: list[int] = []
    for feed_cfg in feeds:
        name = feed_cfg.get("name", "unknown")
        url = feed_cfg.get("url")
        tags = feed_cfg.get("tags", [])

        if not url:
            log.warning("feed_missing_url", name=name)
            continue

        try:
            doc_ids = ingest_feed(
                feed_url=url,
                source_name=name,
                session=session,
                tags=tags,
            )
            all_doc_ids.extend(doc_ids)
        except Exception:
            log.exception("feed_ingestion_error", name=name, url=url)
            # Continue with remaining feeds.
            continue

    return all_doc_ids


# ---------------------------------------------------------------------------
# Default pipeline with built-in handlers
# ---------------------------------------------------------------------------

def get_pipeline() -> IngestionPipeline:
    """Create an IngestionPipeline pre-loaded with all built-in handlers."""
    pipeline = IngestionPipeline()
    pipeline.register("news", _news_handler)
    # Future handlers will be registered here:
    # pipeline.register("youtube", _youtube_handler)
    # pipeline.register("substack", _substack_handler)
    # pipeline.register("markets", _markets_handler)
    # pipeline.register("economic", _economic_handler)
    return pipeline
