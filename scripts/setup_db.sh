#!/usr/bin/env bash
# Initialize PostgreSQL database with pgvector extension for Arlo
# and apply Alembic migrations.
#
# Prerequisites:
#   brew install postgresql@16 pgvector
#   pip install -e ".[dev]"
#
# Usage:
#   ./scripts/setup_db.sh

set -euo pipefail

DB_NAME="${ARLO_DB_NAME:-arlo}"

echo "Creating database '$DB_NAME'..."
createdb "$DB_NAME" 2>/dev/null || echo "Database '$DB_NAME' already exists."

echo "Enabling pgvector extension..."
psql "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "Running Alembic migrations..."
export DATABASE_URL="postgresql://localhost/$DB_NAME"
alembic upgrade head

echo "Done. Database '$DB_NAME' is ready."
