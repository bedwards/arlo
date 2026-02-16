"""YouTube transcript ingestion via yt-dlp and caption extraction.

Uses yt-dlp to list channel videos and extract subtitles/captions.
Prefers manually uploaded captions, falls back to auto-generated ones.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from arlo.db.models import Document, Source

log = structlog.get_logger()

# Try importing the embedder; it may not be available yet (built concurrently).
try:
    from arlo.ingest.embedder import embed_document  # type: ignore[import-untyped]

    _HAS_EMBEDDER = True
except (ImportError, AttributeError):
    _HAS_EMBEDDER = False
    log.warning("embedder_not_available", msg="Embedder module not ready; chunks will not be created")


# ---------------------------------------------------------------------------
# yt-dlp helpers
# ---------------------------------------------------------------------------


def get_channel_videos(
    channel_id: str,
    since: datetime | None = None,
    limit: int = 50,
) -> list[dict]:
    """List recent videos from a YouTube channel.

    Args:
        channel_id: YouTube channel handle (e.g. ``@pbsnewshour``) or ID.
        since: Only include videos published after this datetime.
        limit: Maximum number of videos to return.

    Returns:
        List of dicts with keys: id, title, upload_date, url, duration, description.
    """
    # Build the channel URL. Handles both @handle and raw channel ID formats.
    if channel_id.startswith("@"):
        channel_url = f"https://www.youtube.com/{channel_id}/videos"
    elif channel_id.startswith("UC"):
        channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
    else:
        channel_url = f"https://www.youtube.com/{channel_id}/videos"

    # yt-dlp options: extract flat playlist (metadata only, no download)
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", str(limit),
        "--no-warnings",
        channel_url,
    ]

    # If we have a date filter, add --dateafter
    if since is not None:
        date_str = since.strftime("%Y%m%d")
        cmd.extend(["--dateafter", date_str])

    log.info("listing_channel_videos", channel_id=channel_id, limit=limit, since=since)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        log.error("yt_dlp_timeout", channel_id=channel_id)
        return []
    except FileNotFoundError:
        log.error("yt_dlp_not_found", msg="yt-dlp is not installed or not on PATH")
        return []

    if result.returncode != 0:
        log.error("yt_dlp_list_error", channel_id=channel_id, stderr=result.stderr[:500])
        return []

    videos: list[dict] = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        video_id = entry.get("id", "")
        upload_date_raw = entry.get("upload_date", "")

        # Parse upload_date (YYYYMMDD) into datetime
        published_at: datetime | None = None
        if upload_date_raw and len(upload_date_raw) == 8:
            try:
                published_at = datetime.strptime(upload_date_raw, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass

        # Apply the since filter for flat-playlist results (--dateafter may not
        # work reliably with flat-playlist mode on all channel types).
        if since is not None and published_at is not None and published_at <= since:
            continue

        videos.append(
            {
                "id": video_id,
                "title": entry.get("title", ""),
                "upload_date": upload_date_raw,
                "published_at": published_at,
                "url": entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
                "duration": entry.get("duration"),
                "description": entry.get("description", ""),
            }
        )

    log.info("channel_videos_found", channel_id=channel_id, count=len(videos))
    return videos


def get_transcript(video_id: str) -> str | None:
    """Extract the transcript (captions) for a YouTube video.

    Prefers manually uploaded English captions, falls back to auto-generated.
    Returns the plain-text transcript, or None if no captions are available.

    Args:
        video_id: YouTube video ID (the 11-character string).

    Returns:
        Transcript text or None.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = str(Path(tmpdir) / "%(id)s")

        # Try manual captions first, then auto-generated
        for auto_flag in (False, True):
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--sub-lang", "en",
                "--sub-format", "vtt",
                "--output", output_template,
                "--no-warnings",
                video_url,
            ]

            if auto_flag:
                cmd.append("--write-auto-subs")
            else:
                cmd.append("--write-subs")
                cmd.append("--no-write-auto-subs")

            log.debug(
                "extracting_transcript",
                video_id=video_id,
                auto=auto_flag,
            )

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                log.warning("transcript_timeout", video_id=video_id, auto=auto_flag)
                continue
            except FileNotFoundError:
                log.error("yt_dlp_not_found", msg="yt-dlp is not installed or not on PATH")
                return None

            # Look for the generated subtitle file
            sub_files = list(Path(tmpdir).glob(f"{video_id}*.vtt"))
            if not sub_files:
                # Also check for .en.vtt pattern
                sub_files = list(Path(tmpdir).glob("*.en.vtt"))

            if sub_files:
                raw_vtt = sub_files[0].read_text(encoding="utf-8", errors="replace")
                transcript = _parse_vtt(raw_vtt)
                if transcript and transcript.strip():
                    log.info(
                        "transcript_extracted",
                        video_id=video_id,
                        auto=auto_flag,
                        length=len(transcript),
                    )
                    return transcript

    log.warning("no_transcript_available", video_id=video_id)
    return None


def _parse_vtt(vtt_text: str) -> str:
    """Parse WebVTT subtitle text into clean plain text.

    Strips timestamps, cue identifiers, VTT headers, and deduplicates
    repeated lines that are common in auto-generated captions.
    """
    lines: list[str] = []
    seen: set[str] = set()

    for line in vtt_text.splitlines():
        stripped = line.strip()

        # Skip VTT header, empty lines, and timestamp lines
        if not stripped:
            continue
        if stripped.startswith("WEBVTT"):
            continue
        if stripped.startswith("Kind:") or stripped.startswith("Language:"):
            continue
        if stripped.startswith("NOTE"):
            continue
        # Timestamp lines: "00:00:01.000 --> 00:00:04.000"
        if "-->" in stripped:
            continue
        # Numeric cue identifiers
        if stripped.isdigit():
            continue

        # Strip HTML-like tags (e.g. <c>, </c>, <00:00:01.000>)
        cleaned = re.sub(r"<[^>]+>", "", stripped)
        cleaned = cleaned.strip()

        if not cleaned:
            continue

        # Deduplicate consecutive identical lines (common in auto-captions)
        if cleaned not in seen:
            lines.append(cleaned)
            seen.add(cleaned)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Source / config helpers
# ---------------------------------------------------------------------------


def _load_youtube_channels() -> list[dict]:
    """Load YouTube channel config from sources.toml."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    sources_path = Path("config/sources.toml")
    if not sources_path.exists():
        log.warning("sources_toml_not_found", path=str(sources_path))
        return []

    with open(sources_path, "rb") as f:
        data = tomllib.load(f)

    youtube_section = data.get("youtube", {})
    channels = youtube_section.get("channels", [])
    return channels


def _get_or_create_source(session: Session, channel_id: str, channel_name: str) -> Source:
    """Get existing Source record or create a new one for a YouTube channel."""
    source = (
        session.query(Source)
        .filter(Source.source_type == "youtube", Source.name == channel_name)
        .first()
    )
    if source is None:
        source = Source(
            name=channel_name,
            source_type="youtube",
            config={"channel_id": channel_id},
            active=True,
        )
        session.add(source)
        session.flush()  # Get the ID assigned
        log.info("source_created", name=channel_name, source_id=source.id)
    return source


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------


def ingest_channel(channel_id: str, channel_name: str, session: Session) -> int:
    """Run the full ingestion pipeline for a single YouTube channel.

    1. Get or create Source record.
    2. List recent videos (since last_fetched).
    3. For each video, skip if already ingested (by external_id).
    4. Extract transcript.
    5. Store Document with metadata.
    6. Embed and chunk via shared embedder (if available).

    Args:
        channel_id: YouTube channel handle or ID.
        channel_name: Human-readable channel name.
        session: SQLAlchemy session.

    Returns:
        Number of new documents ingested.
    """
    source = _get_or_create_source(session, channel_id, channel_name)

    # Get videos since last fetch
    since = source.last_fetched
    videos = get_channel_videos(channel_id, since=since)

    if not videos:
        log.info("no_new_videos", channel=channel_name, since=since)
        return 0

    ingested_count = 0

    for video in videos:
        video_id = video["id"]
        if not video_id:
            continue

        # Check for existing document (deduplication by external_id)
        existing = (
            session.query(Document)
            .filter(Document.source_id == source.id, Document.external_id == video_id)
            .first()
        )
        if existing is not None:
            log.debug("video_already_ingested", video_id=video_id, title=video["title"])
            continue

        # Extract transcript
        transcript = get_transcript(video_id)
        if transcript is None:
            log.warning(
                "skipping_video_no_transcript",
                video_id=video_id,
                title=video["title"],
            )
            continue

        # Build video URL
        video_url = video.get("url") or f"https://www.youtube.com/watch?v={video_id}"

        # Create Document record
        doc = Document(
            source_id=source.id,
            external_id=video_id,
            title=video.get("title"),
            author=channel_name,
            published_at=video.get("published_at"),
            url=video_url,
            full_text=transcript,
            metadata_={
                "channel": channel_name,
                "channel_id": channel_id,
                "duration": video.get("duration"),
                "upload_date": video.get("upload_date"),
                "description": (video.get("description") or "")[:1000],
                "source_type": "youtube_transcript",
            },
        )
        session.add(doc)
        session.flush()  # Get doc.id for embedding

        log.info(
            "document_created",
            video_id=video_id,
            title=video.get("title"),
            doc_id=doc.id,
            transcript_length=len(transcript),
        )

        # Embed and chunk (if embedder is available)
        if _HAS_EMBEDDER:
            try:
                embed_document(doc, session)
                log.info("document_embedded", doc_id=doc.id)
            except Exception:
                log.exception("embedding_failed", doc_id=doc.id)
        else:
            log.debug("skipping_embedding", doc_id=doc.id, reason="embedder not available")

        ingested_count += 1

    # Update source last_fetched timestamp
    source.last_fetched = datetime.now(timezone.utc)
    session.commit()

    log.info(
        "channel_ingestion_complete",
        channel=channel_name,
        new_documents=ingested_count,
        total_videos_checked=len(videos),
    )
    return ingested_count


def ingest_youtube(channel_filter: str | None = None) -> int:
    """Ingest transcripts from all configured YouTube channels (or a specific one).

    Reads channel list from config/sources.toml, creates DB sessions,
    and runs the ingestion pipeline for each channel.

    Args:
        channel_filter: If provided, only ingest this channel (by handle or name).

    Returns:
        Total number of new documents ingested.
    """
    from arlo.db.postgres import get_session

    channels = _load_youtube_channels()
    if not channels:
        log.warning("no_youtube_channels_configured")
        return 0

    # Filter to specific channel if requested
    if channel_filter is not None:
        normalized = channel_filter.lower().strip().lstrip("@")
        channels = [
            ch
            for ch in channels
            if normalized in ch.get("channel_id", "").lower().lstrip("@")
            or normalized in ch.get("name", "").lower()
        ]
        if not channels:
            log.error("channel_not_found", filter=channel_filter)
            return 0

    total = 0
    session = get_session()

    try:
        for ch in channels:
            ch_id = ch.get("channel_id", "")
            ch_name = ch.get("name", ch_id)
            log.info("ingesting_channel", channel=ch_name, channel_id=ch_id)
            try:
                count = ingest_channel(ch_id, ch_name, session)
                total += count
            except Exception:
                log.exception("channel_ingestion_failed", channel=ch_name)
                session.rollback()
                continue
    finally:
        session.close()

    log.info("youtube_ingestion_complete", total_new_documents=total)
    return total
