"""Initial schema — all tables from SPEC.

Revision ID: 001
Revises: None
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Embedding dimension for sentence-transformers all-MiniLM-L6-v2
EMBEDDING_DIM = 384


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- sources ---
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("source_type", sa.Text, nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False),
        sa.Column("last_fetched", sa.DateTime(timezone=True)),
        sa.Column("active", sa.Boolean, server_default=sa.text("true")),
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id")),
        sa.Column("external_id", sa.Text),
        sa.Column("title", sa.Text),
        sa.Column("author", sa.Text),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("url", sa.Text),
        sa.Column("full_text", sa.Text),
        sa.Column("metadata", postgresql.JSONB),
    )

    # --- chunks (without embedding — added via raw SQL for pgvector type) ---
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id")),
        sa.Column("chunk_index", sa.Integer),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer),
    )
    # Add the vector column via raw SQL (pgvector type)
    op.execute(f"ALTER TABLE chunks ADD COLUMN embedding vector({EMBEDDING_DIM})")
    # IVFFlat index on the embedding column
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # --- market_snapshots ---
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("platform", sa.Text, nullable=False),
        sa.Column("market_id", sa.Text, nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("question_text", sa.Text),
        sa.Column("current_probability", sa.Float),
        sa.Column("volume", sa.Float),
        sa.Column("close_date", sa.DateTime(timezone=True)),
        sa.Column("resolution", sa.Text),
        sa.Column(
            "snapshot_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("metadata", postgresql.JSONB),
    )

    # --- economic_series (composite primary key) ---
    op.create_table(
        "economic_series",
        sa.Column("series_id", sa.Text, primary_key=True),
        sa.Column("source", sa.Text, primary_key=True),
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("value", sa.Float),
    )

    # --- domains ---
    op.create_table(
        "domains",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("attention_trajectory", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # --- domain_questions_raw ---
    op.create_table(
        "domain_questions_raw",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("domain_id", sa.Integer, sa.ForeignKey("domains.id")),
        sa.Column("raw_question_text", sa.Text, nullable=False),
        sa.Column("source_technique", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # --- questions ---
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("domain_id", sa.Integer, sa.ForeignKey("domains.id")),
        sa.Column("parent_question_id", sa.Integer, sa.ForeignKey("questions.id")),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("question_type", sa.Text, nullable=False),
        sa.Column("resolution_criteria", sa.Text, nullable=False),
        sa.Column("resolution_source", sa.Text),
        sa.Column("open_date", sa.Date, nullable=False),
        sa.Column("close_date", sa.Date, nullable=False),
        sa.Column("base_rate", sa.Float),
        sa.Column("is_novel", sa.Boolean, server_default=sa.text("false")),
        sa.Column("information_value", sa.Text),
        sa.Column("tradeable_on", postgresql.JSONB),
        sa.Column("status", sa.Text, server_default=sa.text("'active'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # --- forecasts ---
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id"), nullable=False),
        sa.Column(
            "forecast_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("probability", sa.Float, nullable=False),
        sa.Column("confidence_interval_low", sa.Float),
        sa.Column("confidence_interval_high", sa.Float),
        sa.Column("components", postgresql.JSONB, nullable=False),
        sa.Column("aggregation_method", sa.Text),
        sa.Column("extremization_d", sa.Float),
        sa.Column("reasoning_summary", sa.Text),
        sa.Column("key_uncertainties", postgresql.ARRAY(sa.Text)),
        sa.Column("update_triggers", postgresql.ARRAY(sa.Text)),
        sa.UniqueConstraint("question_id", "forecast_date", name="uq_forecast_question_date"),
    )

    # --- forecast_scores ---
    op.create_table(
        "forecast_scores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("forecast_id", sa.Integer, sa.ForeignKey("forecasts.id"), nullable=False),
        sa.Column("resolution_value", sa.Float),
        sa.Column("brier_score", sa.Float),
        sa.Column("log_score", sa.Float),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    # --- positions ---
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("platform", sa.Text, nullable=False),
        sa.Column("market_id", sa.Text, nullable=False),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id")),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column(
            "entry_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("exit_price", sa.Float),
        sa.Column("exit_date", sa.DateTime(timezone=True)),
        sa.Column("pnl", sa.Float),
        sa.Column("cassandra_prob_at_entry", sa.Float),
        sa.Column("market_prob_at_entry", sa.Float),
        sa.Column("edge_at_entry", sa.Float),
        sa.Column("status", sa.Text, server_default=sa.text("'open'")),
    )

    # --- trade_log ---
    op.create_table(
        "trade_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("position_id", sa.Integer, sa.ForeignKey("positions.id")),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("human_confirmed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("confirmation_timestamp", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("trade_log")
    op.drop_table("positions")
    op.drop_table("forecast_scores")
    op.drop_table("forecasts")
    op.drop_table("questions")
    op.drop_table("domain_questions_raw")
    op.drop_table("domains")
    op.drop_table("economic_series")
    op.drop_table("market_snapshots")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("sources")
    op.execute("DROP EXTENSION IF EXISTS vector")
