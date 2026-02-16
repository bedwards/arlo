"""Substack post ingestion via RSS feeds.

Fetches full-text articles from Substack RSS feeds, cleans HTML to plain text,
and stores them in the Document table with proper deduplication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import structlog
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from arlo.db.models import Document, Source
from arlo.db.postgres import get_session

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

log = structlog.get_logger(__name__)

SOURCES_TOML_PATH = Path("config/sources.toml")
SOURCE_TYPE = "substack"


# ---------------------------------------------------------------------------
# RSS feed parsing
# ---------------------------------------------------------------------------


def fetch_substack_feed(feed_url: str) -> list[dict[str, Any]]:
    """Parse a Substack RSS feed and return a list of post dicts.

    Each dict contains:
        - title: str
        - author: str | None
        - url: str (the article link)
        - published: datetime | None
        - content_html: str (raw HTML body from the feed)
        - summary: str | None
    """
    log.info("fetching_substack_feed", url=feed_url)
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        log.error("feed_parse_error", url=feed_url, error=str(feed.bozo_exception))
        return []

    posts: list[dict[str, Any]] = []
    for entry in feed.entries:
        # Substack RSS includes full HTML in content[0].value
        content_html = ""
        if hasattr(entry, "content") and entry.content:
            content_html = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content_html = entry.summary or ""

        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass

        author = getattr(entry, "author", None)

        posts.append(
            {
                "title": getattr(entry, "title", "Untitled"),
                "author": author,
                "url": getattr(entry, "link", ""),
                "published": published,
                "content_html": content_html,
                "summary": getattr(entry, "summary", None),
            }
        )

    log.info("feed_parsed", url=feed_url, post_count=len(posts))
    return posts


# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------


def html_to_plain_text(html: str) -> str:
    """Convert HTML content to clean plain text.

    Strips all tags, collapses whitespace, and preserves paragraph breaks.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style"]):
        element.decompose()

    # Get text with newlines for block elements
    text = soup.get_text(separator="\n")

    # Collapse multiple blank lines into double newlines (paragraph breaks)
    lines = []
    prev_blank = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if not prev_blank:
                lines.append("")
                prev_blank = True
        else:
            lines.append(stripped)
            prev_blank = False

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Source management
# ---------------------------------------------------------------------------


def _get_or_create_source(session: Session, publication_name: str, feed_url: str) -> Source:
    """Find or create a Source record for the given Substack publication."""
    source = (
        session.query(Source)
        .filter(Source.source_type == SOURCE_TYPE, Source.name == publication_name)
        .first()
    )
    if source is None:
        source = Source(
            name=publication_name,
            source_type=SOURCE_TYPE,
            config={"feed_url": feed_url},
            active=True,
        )
        session.add(source)
        session.flush()  # get the id
        log.info("source_created", name=publication_name, source_id=source.id)
    return source


# ---------------------------------------------------------------------------
# Publication ingestion
# ---------------------------------------------------------------------------


def ingest_publication(
    feed_url: str,
    publication_name: str,
    session: Session,
    tags: list[str] | None = None,
) -> int:
    """Ingest all posts from a single Substack publication's RSS feed.

    Pipeline:
      1. Parse RSS feed
      2. Extract full text from feed content (Substack RSS includes full HTML)
      3. Clean HTML to plain text via beautifulsoup4
      4. Store in Document table (article URL as external_id for dedup)
      5. Chunk and embed via shared embedder (if available)

    Returns the number of new documents ingested.
    """
    source = _get_or_create_source(session, publication_name, feed_url)
    posts = fetch_substack_feed(feed_url)

    if not posts:
        log.warning("no_posts_found", publication=publication_name, url=feed_url)
        return 0

    new_count = 0

    for post in posts:
        external_id = post["url"]
        if not external_id:
            log.warning("skipping_post_no_url", title=post["title"])
            continue

        # Deduplication: skip if we already have this article
        existing = (
            session.query(Document)
            .filter(Document.source_id == source.id, Document.external_id == external_id)
            .first()
        )
        if existing is not None:
            log.debug("skipping_duplicate", external_id=external_id)
            continue

        # Clean HTML to plain text
        full_text = html_to_plain_text(post["content_html"])
        if not full_text:
            log.warning("skipping_empty_content", url=external_id, title=post["title"])
            continue

        metadata = {
            "publication": publication_name,
            "tags": tags or [],
        }

        doc = Document(
            source_id=source.id,
            external_id=external_id,
            title=post["title"],
            author=post["author"],
            published_at=post["published"],
            url=external_id,
            full_text=full_text,
            metadata_=metadata,
        )
        session.add(doc)
        new_count += 1
        log.info(
            "document_ingested",
            title=post["title"],
            url=external_id,
            text_length=len(full_text),
        )

    # Update source last_fetched timestamp
    source.last_fetched = datetime.now(timezone.utc)
    session.commit()

    # Attempt chunking and embedding (being built concurrently — graceful fallback)
    try:
        from arlo.ingest.embedder import chunk_and_embed  # type: ignore[attr-defined]

        log.info("running_embedder", publication=publication_name, new_docs=new_count)
        chunk_and_embed(session, source.id)
    except (ImportError, AttributeError):
        log.info(
            "embedder_not_available",
            detail="Chunking/embedding will be done when the embedder module is ready.",
        )

    log.info(
        "publication_ingested",
        publication=publication_name,
        new_documents=new_count,
        total_in_feed=len(posts),
    )
    return new_count


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------


def load_substack_publications(
    sources_path: str | Path = SOURCES_TOML_PATH,
) -> list[dict[str, Any]]:
    """Load Substack publication configs from sources.toml.

    Returns a list of dicts with keys: name, url, tags.
    """
    path = Path(sources_path)
    if not path.exists():
        log.warning("sources_toml_not_found", path=str(path))
        return []

    with open(path, "rb") as f:
        data = tomllib.load(f)

    publications = data.get("substack", {}).get("publications", [])
    log.info("loaded_substack_publications", count=len(publications))
    return publications


# ---------------------------------------------------------------------------
# Top-level ingestion entry point
# ---------------------------------------------------------------------------


def ingest_all_substacks(
    publication_filter: str | None = None,
    sources_path: str | Path = SOURCES_TOML_PATH,
) -> int:
    """Ingest all configured Substack publications (or a specific one).

    Args:
        publication_filter: If provided, only ingest the publication whose name
            contains this string (case-insensitive).
        sources_path: Path to sources.toml config file.

    Returns:
        Total number of new documents ingested across all publications.
    """
    publications = load_substack_publications(sources_path)
    if not publications:
        log.warning("no_substack_publications_configured")
        return 0

    if publication_filter:
        publications = [
            p
            for p in publications
            if publication_filter.lower() in p.get("name", "").lower()
        ]
        if not publications:
            log.warning(
                "no_matching_publication",
                filter=publication_filter,
            )
            return 0

    session = get_session()
    total_new = 0

    try:
        for pub in publications:
            name = pub.get("name", "Unknown")
            url = pub.get("url", "")
            tags = pub.get("tags", [])

            if not url:
                log.warning("skipping_publication_no_url", name=name)
                continue

            log.info("ingesting_publication", name=name, url=url)
            try:
                count = ingest_publication(url, name, session, tags=tags)
                total_new += count
            except Exception:
                log.exception("publication_ingest_failed", name=name, url=url)
                # Continue with other publications
                continue
    finally:
        session.close()

    log.info("substack_ingestion_complete", total_new_documents=total_new)
    return total_new
