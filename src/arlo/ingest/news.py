"""News feed ingestion via RSS/Atom and feedparser.

Provides generic RSS/Atom feed parsing and a high-level ``ingest_feed``
function that fetches a feed, deduplicates by URL (external_id), stores
new articles in the Document table, and returns the list of newly created
document IDs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import feedparser
import structlog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Feed parsing helpers
# ---------------------------------------------------------------------------


def _parse_published(entry) -> datetime | None:
    """Extract a timezone-aware published datetime from a feedparser entry."""
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed is None:
        return None
    try:
        from time import mktime

        ts = mktime(published_parsed)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _extract_full_text(entry) -> str:
    """Best-effort extraction of article body from a feed entry.

    Prefers ``content`` (Atom full content) over ``summary`` (RSS description).
    Falls back to empty string.
    """
    # Atom content blocks
    if "content" in entry:
        for content_block in entry["content"]:
            value = content_block.get("value", "")
            if value:
                return value

    # RSS summary / description
    return entry.get("summary", "") or ""


def fetch_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS/Atom feed, returning a list of article dicts.

    Each dict contains:
      - title (str)
      - author (str | None)
      - published_at (datetime | None)
      - url (str)
      - full_text (str)
    """
    log.info("fetching_feed", url=url)
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        log.warning("feed_parse_error", url=url, error=str(feed.bozo_exception))
        return []

    articles: list[dict] = []
    for entry in feed.entries:
        link = entry.get("link", "")
        if not link:
            continue

        articles.append(
            {
                "title": entry.get("title", ""),
                "author": entry.get("author"),
                "published_at": _parse_published(entry),
                "url": link,
                "full_text": _extract_full_text(entry),
            }
        )

    log.info("feed_parsed", url=url, article_count=len(articles))
    return articles


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def ingest_feed(
    feed_url: str,
    source_name: str,
    session: Session,
    *,
    source_id: int | None = None,
    tags: list[str] | None = None,
) -> list[int]:
    """Fetch an RSS/Atom feed and store new articles as Documents.

    Deduplication is based on the article URL stored as ``external_id``.

    Args:
        feed_url: URL of the RSS/Atom feed.
        source_name: Human-readable name (e.g. "Texas Tribune").
        session: Active SQLAlchemy session (caller manages commit/rollback).
        source_id: Optional FK to the ``sources`` table.
        tags: Optional list of tags to store in document metadata.

    Returns:
        List of newly created Document IDs.
    """
    from arlo.db.models import Document

    articles = fetch_feed(feed_url)
    if not articles:
        log.info("no_articles", feed_url=feed_url)
        return []

    # Gather external_ids for batch dedup lookup.
    article_urls = [a["url"] for a in articles]
    existing = set(
        row[0]
        for row in session.query(Document.external_id)
        .filter(Document.external_id.in_(article_urls))
        .all()
    )

    new_doc_ids: list[int] = []
    for article in articles:
        if article["url"] in existing:
            log.debug("skipping_duplicate", url=article["url"])
            continue

        doc = Document(
            source_id=source_id,
            external_id=article["url"],
            title=article["title"],
            author=article["author"],
            published_at=article["published_at"],
            url=article["url"],
            full_text=article["full_text"],
            metadata_={"source_name": source_name, "tags": tags or []},
        )
        session.add(doc)
        session.flush()  # populate doc.id
        new_doc_ids.append(doc.id)

        log.info(
            "document_stored",
            title=article["title"][:80],
            doc_id=doc.id,
            url=article["url"],
        )

    log.info(
        "feed_ingestion_complete",
        source=source_name,
        new=len(new_doc_ids),
        skipped=len(articles) - len(new_doc_ids),
    )
    return new_doc_ids
