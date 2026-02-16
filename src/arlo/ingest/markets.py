"""Prediction market data ingestion from Metaculus, Kalshi, Polymarket, Manifold."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from arlo.db.models import MarketSnapshot

log = structlog.get_logger(__name__)

# Rate limiting: minimum seconds between API calls per platform
_RATE_LIMIT_SECONDS = 1.0

# Education-related keywords for market filtering
EDUCATION_KEYWORDS = [
    "education",
    "school",
    "college",
    "university",
    "student",
    "teacher",
    "tuition",
    "enrollment",
]

# ---------------------------------------------------------------------------
# Metaculus
# ---------------------------------------------------------------------------

METACULUS_BASE = "https://www.metaculus.com/api2"


def fetch_metaculus_questions(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch open questions from Metaculus with community predictions.

    Returns a list of dicts with keys:
        id, title, question_text, community_prediction, resolution_date, raw
    """
    url = f"{METACULUS_BASE}/questions/"
    params = {"status": "open", "limit": limit, "type": "forecast"}
    results: list[dict[str, Any]] = []

    log.info("metaculus.fetch_start", limit=limit)
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        questions = data.get("results", [])
        for q in questions:
            # Community prediction can be nested in different places
            community_pred = None
            forecasts = q.get("community_prediction", {})
            if isinstance(forecasts, dict):
                community_pred = forecasts.get("full", {}).get("q2")
            elif isinstance(forecasts, (int, float)):
                community_pred = float(forecasts)

            # Try alternate location for prediction
            if community_pred is None:
                community_pred = q.get("prediction_count") and q.get("community_prediction")

            close_date = None
            close_time_str = q.get("scheduled_close_time") or q.get("resolve_time")
            if close_time_str:
                try:
                    close_date = datetime.fromisoformat(
                        close_time_str.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            results.append({
                "id": str(q.get("id", "")),
                "title": q.get("title", ""),
                "question_text": q.get("title_short", q.get("title", "")),
                "community_prediction": community_pred,
                "resolution_date": close_date,
                "raw": q,
            })

        log.info("metaculus.fetch_done", count=len(results))
    except httpx.HTTPError as exc:
        log.error("metaculus.fetch_error", error=str(exc))
    except Exception as exc:
        log.error("metaculus.fetch_error", error=str(exc), exc_info=True)

    return results


# ---------------------------------------------------------------------------
# Kalshi
# ---------------------------------------------------------------------------


def fetch_kalshi_markets(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch open markets from Kalshi via the kalshi-python SDK.

    Returns a list of dicts with keys:
        ticker, title, yes_price, volume, close_date, raw
    """
    results: list[dict[str, Any]] = []
    log.info("kalshi.fetch_start", limit=limit)

    try:
        from arlo.trade.kalshi_client import get_client, get_markets

        client = get_client()
        markets = get_markets(client, status="open", limit=limit)

        for m in markets:
            close_date = None
            close_time_str = getattr(m, "close_time", None) or getattr(m, "expiration_time", None)
            if close_time_str:
                try:
                    close_date = datetime.fromisoformat(
                        str(close_time_str).replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            yes_price = getattr(m, "yes_price", None)
            probability = yes_price / 100.0 if yes_price is not None else None

            results.append({
                "ticker": getattr(m, "ticker", ""),
                "title": getattr(m, "title", ""),
                "yes_price": yes_price,
                "probability": probability,
                "volume": getattr(m, "volume", None),
                "close_date": close_date,
                "raw": {
                    k: v for k, v in vars(m).items()
                    if not k.startswith("_") and _is_jsonable(v)
                },
            })

        log.info("kalshi.fetch_done", count=len(results))
    except ImportError:
        log.error("kalshi.import_error", msg="kalshi-python not installed")
    except KeyError as exc:
        log.error("kalshi.auth_error", error=str(exc), msg="Missing Kalshi credentials")
    except Exception as exc:
        log.error("kalshi.fetch_error", error=str(exc), exc_info=True)

    return results


# ---------------------------------------------------------------------------
# Polymarket
# ---------------------------------------------------------------------------

POLYMARKET_BASE = "https://clob.polymarket.com"


def fetch_polymarket_markets(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch markets from Polymarket public CLOB API.

    Returns a list of dicts with keys:
        condition_id, question, outcome_prices, volume, raw
    """
    results: list[dict[str, Any]] = []
    log.info("polymarket.fetch_start", limit=limit)

    try:
        with httpx.Client(timeout=30) as client:
            # The CLOB API uses /markets for public market data
            resp = client.get(
                f"{POLYMARKET_BASE}/markets",
                params={"limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()

        # Response can be a list or have a "data"/"markets" key
        markets = data if isinstance(data, list) else data.get("data", data.get("markets", []))

        for m in markets:
            # Extract outcome prices
            outcome_prices = None
            tokens = m.get("tokens", [])
            if tokens:
                outcome_prices = {
                    t.get("outcome", f"token_{i}"): t.get("price")
                    for i, t in enumerate(tokens)
                    if t.get("price") is not None
                }

            # Try to get a probability from outcome prices
            probability = None
            if outcome_prices:
                # Look for "Yes" outcome price
                for key in ("Yes", "yes", "YES"):
                    if key in outcome_prices:
                        probability = outcome_prices[key]
                        break
                # If not found, take first token price
                if probability is None and outcome_prices:
                    probability = next(iter(outcome_prices.values()), None)

            close_date = None
            end_date_str = m.get("end_date_iso") or m.get("expiration_date")
            if end_date_str:
                try:
                    close_date = datetime.fromisoformat(
                        end_date_str.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            volume_raw = m.get("volume") or m.get("volume_num") or m.get("volumeNum")
            volume = float(volume_raw) if volume_raw is not None else None

            results.append({
                "condition_id": m.get("condition_id", m.get("id", "")),
                "question": m.get("question", m.get("title", "")),
                "outcome_prices": outcome_prices,
                "probability": probability,
                "volume": volume,
                "close_date": close_date,
                "raw": m,
            })

        log.info("polymarket.fetch_done", count=len(results))
    except httpx.HTTPError as exc:
        log.error("polymarket.fetch_error", error=str(exc))
    except Exception as exc:
        log.error("polymarket.fetch_error", error=str(exc), exc_info=True)

    return results


# ---------------------------------------------------------------------------
# Manifold Markets
# ---------------------------------------------------------------------------

MANIFOLD_BASE = "https://api.manifold.markets/v0"


def fetch_manifold_markets(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch markets from Manifold Markets public API.

    Returns a list of dicts with keys:
        id, question, probability, volume, close_time, raw
    """
    results: list[dict[str, Any]] = []
    log.info("manifold.fetch_start", limit=limit)

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{MANIFOLD_BASE}/markets",
                params={"limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()

        markets = data if isinstance(data, list) else data.get("data", [])

        for m in markets:
            close_date = None
            close_ts = m.get("closeTime")
            if close_ts:
                try:
                    # Manifold uses millisecond timestamps
                    close_date = datetime.fromtimestamp(
                        close_ts / 1000, tz=timezone.utc
                    )
                except (ValueError, TypeError, OSError):
                    pass

            probability = m.get("probability")
            volume = m.get("volume")
            if volume is not None:
                volume = float(volume)

            results.append({
                "id": str(m.get("id", "")),
                "question": m.get("question", ""),
                "probability": probability,
                "volume": volume,
                "close_time": close_date,
                "raw": m,
            })

        log.info("manifold.fetch_done", count=len(results))
    except httpx.HTTPError as exc:
        log.error("manifold.fetch_error", error=str(exc))
    except Exception as exc:
        log.error("manifold.fetch_error", error=str(exc), exc_info=True)

    return results


# ---------------------------------------------------------------------------
# Education market search
# ---------------------------------------------------------------------------


def search_education_markets(
    snapshots: list[MarketSnapshot] | None = None,
    session=None,
) -> list[MarketSnapshot]:
    """Filter market snapshots by education-related keywords.

    If snapshots are provided, filters those directly. Otherwise queries the
    database via the given session (or creates one).

    Args:
        snapshots: Optional list of MarketSnapshot objects to filter in-memory.
        session: Optional SQLAlchemy session to query from DB.

    Returns:
        List of MarketSnapshot objects matching education keywords.
    """
    if snapshots is not None:
        return _filter_education(snapshots)

    # Query from database
    if session is None:
        from arlo.db.postgres import get_session
        session = get_session()

    all_snapshots = session.query(MarketSnapshot).all()
    return _filter_education(all_snapshots)


def _filter_education(snapshots: list[MarketSnapshot]) -> list[MarketSnapshot]:
    """Filter snapshots matching any education keyword in title or question_text."""
    results = []
    for snap in snapshots:
        text = " ".join(
            part.lower()
            for part in [snap.title or "", snap.question_text or ""]
        )
        if any(kw in text for kw in EDUCATION_KEYWORDS):
            results.append(snap)
    return results


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------


def ingest_markets(session=None) -> list[MarketSnapshot]:
    """Fetch markets from all platforms and store snapshots in the database.

    Each platform fetch is independent — if one fails, the others continue.
    Rate limiting is applied between platform fetches.

    Args:
        session: Optional SQLAlchemy session. If None, creates one via get_session.

    Returns:
        List of MarketSnapshot objects that were added.
    """
    if session is None:
        from arlo.db.postgres import get_session
        session = get_session()

    all_snapshots: list[MarketSnapshot] = []
    now = datetime.now(timezone.utc)

    # --- Metaculus ---
    log.info("ingest_markets.platform_start", platform="metaculus")
    metaculus_questions = fetch_metaculus_questions()
    for q in metaculus_questions:
        snap = MarketSnapshot(
            platform="metaculus",
            market_id=q["id"],
            title=q["title"],
            question_text=q["question_text"],
            current_probability=q["community_prediction"],
            volume=None,  # Metaculus doesn't expose volume
            close_date=q["resolution_date"],
            resolution=None,
            snapshot_at=now,
            metadata_=_safe_metadata(q["raw"]),
        )
        session.add(snap)
        all_snapshots.append(snap)
    log.info("ingest_markets.platform_done", platform="metaculus", count=len(metaculus_questions))

    time.sleep(_RATE_LIMIT_SECONDS)

    # --- Kalshi ---
    log.info("ingest_markets.platform_start", platform="kalshi")
    kalshi_markets = fetch_kalshi_markets()
    for m in kalshi_markets:
        snap = MarketSnapshot(
            platform="kalshi",
            market_id=m["ticker"],
            title=m["title"],
            question_text=m["title"],
            current_probability=m["probability"],
            volume=float(m["volume"]) if m["volume"] is not None else None,
            close_date=m["close_date"],
            resolution=None,
            snapshot_at=now,
            metadata_=_safe_metadata(m["raw"]),
        )
        session.add(snap)
        all_snapshots.append(snap)
    log.info("ingest_markets.platform_done", platform="kalshi", count=len(kalshi_markets))

    time.sleep(_RATE_LIMIT_SECONDS)

    # --- Polymarket ---
    log.info("ingest_markets.platform_start", platform="polymarket")
    poly_markets = fetch_polymarket_markets()
    for m in poly_markets:
        snap = MarketSnapshot(
            platform="polymarket",
            market_id=str(m["condition_id"]),
            title=m["question"],
            question_text=m["question"],
            current_probability=m["probability"],
            volume=m["volume"],
            close_date=m["close_date"],
            resolution=None,
            snapshot_at=now,
            metadata_=_safe_metadata(m["raw"]),
        )
        session.add(snap)
        all_snapshots.append(snap)
    log.info("ingest_markets.platform_done", platform="polymarket", count=len(poly_markets))

    time.sleep(_RATE_LIMIT_SECONDS)

    # --- Manifold ---
    log.info("ingest_markets.platform_start", platform="manifold")
    manifold_mkts = fetch_manifold_markets()
    for m in manifold_mkts:
        snap = MarketSnapshot(
            platform="manifold",
            market_id=m["id"],
            title=m["question"],
            question_text=m["question"],
            current_probability=m["probability"],
            volume=m["volume"],
            close_date=m["close_time"],
            resolution=None,
            snapshot_at=now,
            metadata_=_safe_metadata(m["raw"]),
        )
        session.add(snap)
        all_snapshots.append(snap)
    log.info("ingest_markets.platform_done", platform="manifold", count=len(manifold_mkts))

    # Commit all snapshots
    try:
        session.commit()
        log.info("ingest_markets.committed", total=len(all_snapshots))
    except Exception as exc:
        log.error("ingest_markets.commit_error", error=str(exc))
        session.rollback()
        raise

    return all_snapshots


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_jsonable(val: Any) -> bool:
    """Check if a value is JSON-serializable (for metadata extraction)."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return True
    if isinstance(val, (list, tuple)):
        return all(_is_jsonable(v) for v in val)
    if isinstance(val, dict):
        return all(isinstance(k, str) and _is_jsonable(v) for k, v in val.items())
    return False


def _safe_metadata(raw: Any) -> dict | None:
    """Ensure metadata is JSON-serializable; strip non-serializable values."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None

    clean = {}
    for k, v in raw.items():
        if _is_jsonable(v):
            clean[k] = v
        else:
            # Convert to string representation as fallback
            try:
                clean[k] = str(v)
            except Exception:
                pass
    return clean if clean else None
