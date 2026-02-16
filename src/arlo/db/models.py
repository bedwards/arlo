"""SQLAlchemy ORM models for all Arlo database tables.

Uses pgvector for embedding storage and JSONB for flexible metadata columns.
Embedding dimension is 384 (sentence-transformers all-MiniLM-L6-v2).
"""

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from arlo.db.postgres import Base

# ---------------------------------------------------------------------------
# Embedding dimension — all-MiniLM-L6-v2
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 384


# ---------------------------------------------------------------------------
# Stage 1 — Ingest
# ---------------------------------------------------------------------------


class Source(Base):
    """Configurable signal source (YouTube channel, Substack, RSS feed, API, etc.)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)  # youtube, substack, rss, api, bulk_csv
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    last_fetched: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="source")


class Document(Base):
    """Ingested document (article, transcript, filing, etc.)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    url: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    source: Mapped["Source | None"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(Base):
    """Text chunk with its vector embedding, linked to a parent document."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    chunk_index: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(EMBEDDING_DIM))
    token_count: Mapped[int | None] = mapped_column(Integer)

    document: Mapped["Document | None"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index(
            "ix_chunks_embedding",
            embedding,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# ---------------------------------------------------------------------------
# Market & economic data
# ---------------------------------------------------------------------------


class MarketSnapshot(Base):
    """Point-in-time snapshot of a prediction market contract."""

    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    market_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    question_text: Mapped[str | None] = mapped_column(Text)
    current_probability: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)


class EconomicSeries(Base):
    """Single data point in an economic time series (FRED, World Bank, BLS, etc.)."""

    __tablename__ = "economic_series"

    series_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float | None] = mapped_column(Float)


# ---------------------------------------------------------------------------
# Stage 2 — Discover
# ---------------------------------------------------------------------------


class Domain(Base):
    """Identified topic domain with its attention trajectory."""

    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    attention_trajectory: Mapped[str | None] = mapped_column(Text)  # rising, falling, gap
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    raw_questions: Mapped[list["DomainQuestionRaw"]] = relationship(back_populates="domain")
    questions: Mapped[list["Question"]] = relationship(back_populates="domain")


class DomainQuestionRaw(Base):
    """Unrefined question surfaced during domain discovery (Stage 2)."""

    __tablename__ = "domain_questions_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain_id: Mapped[int | None] = mapped_column(ForeignKey("domains.id"))
    raw_question_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_technique: Mapped[str | None] = mapped_column(Text)  # five_whys, neustadt_may, etc.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    domain: Mapped["Domain | None"] = relationship(back_populates="raw_questions")


# ---------------------------------------------------------------------------
# Stage 3 — Question
# ---------------------------------------------------------------------------


class Question(Base):
    """Operationalized forecasting question with resolution criteria."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain_id: Mapped[int | None] = mapped_column(ForeignKey("domains.id"))
    parent_question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id"))
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(Text, nullable=False)  # binary, numeric, date, multiple_choice
    resolution_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_source: Mapped[str | None] = mapped_column(Text)
    open_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_rate: Mapped[float | None] = mapped_column(Float)
    is_novel: Mapped[bool] = mapped_column(Boolean, default=False)
    information_value: Mapped[str | None] = mapped_column(Text)  # high, medium, low
    tradeable_on: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, default="active")  # active, resolved_yes, resolved_no, voided
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    domain: Mapped["Domain | None"] = relationship(back_populates="questions")
    parent_question: Mapped["Question | None"] = relationship(
        remote_side="Question.id", back_populates="sub_questions"
    )
    sub_questions: Mapped[list["Question"]] = relationship(back_populates="parent_question")
    forecasts: Mapped[list["Forecast"]] = relationship(back_populates="question")
    scores: Mapped[list["ForecastScore"]] = relationship(back_populates="question")
    positions: Mapped[list["Position"]] = relationship(back_populates="question")


# ---------------------------------------------------------------------------
# Stage 4 — Forecast
# ---------------------------------------------------------------------------


class Forecast(Base):
    """Aggregated probabilistic forecast for a question on a given date."""

    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    forecast_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_interval_low: Mapped[float | None] = mapped_column(Float)
    confidence_interval_high: Mapped[float | None] = mapped_column(Float)
    components: Mapped[dict] = mapped_column(JSONB, nullable=False)
    aggregation_method: Mapped[str | None] = mapped_column(Text)
    extremization_d: Mapped[float | None] = mapped_column(Float)
    reasoning_summary: Mapped[str | None] = mapped_column(Text)
    key_uncertainties: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    update_triggers: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    question: Mapped["Question"] = relationship(back_populates="forecasts")
    scores: Mapped[list["ForecastScore"]] = relationship(back_populates="forecast")

    __table_args__ = (
        UniqueConstraint("question_id", "forecast_date", name="uq_forecast_question_date"),
    )


class ForecastScore(Base):
    """Scoring record for a resolved forecast."""

    __tablename__ = "forecast_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    forecast_id: Mapped[int] = mapped_column(ForeignKey("forecasts.id"), nullable=False)
    resolution_value: Mapped[float | None] = mapped_column(Float)
    brier_score: Mapped[float | None] = mapped_column(Float)
    log_score: Mapped[float | None] = mapped_column(Float)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    question: Mapped["Question"] = relationship(back_populates="scores")
    forecast: Mapped["Forecast"] = relationship(back_populates="scores")


# ---------------------------------------------------------------------------
# Stage 5 — Trade
# ---------------------------------------------------------------------------


class Position(Base):
    """Open or closed trading position on a prediction market."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(Text, nullable=False)  # kalshi, forecastex
    market_id: Mapped[str] = mapped_column(Text, nullable=False)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id"))
    direction: Mapped[str] = mapped_column(Text, nullable=False)  # yes, no
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    exit_price: Mapped[float | None] = mapped_column(Float)
    exit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pnl: Mapped[float | None] = mapped_column(Float)
    cassandra_prob_at_entry: Mapped[float | None] = mapped_column(Float)
    market_prob_at_entry: Mapped[float | None] = mapped_column(Float)
    edge_at_entry: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text, default="open")  # open, closed, expired

    question: Mapped["Question | None"] = relationship(back_populates="positions")
    trade_logs: Mapped[list["TradeLog"]] = relationship(back_populates="position")


class TradeLog(Base):
    """Individual trade execution record within a position."""

    __tablename__ = "trade_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))
    action: Mapped[str] = mapped_column(Text, nullable=False)  # open, close, partial_close
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    human_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmation_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    position: Mapped["Position | None"] = relationship(back_populates="trade_logs")
