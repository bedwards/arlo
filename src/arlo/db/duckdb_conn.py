"""DuckDB connection for analytical queries on economic time series."""

import os

import duckdb


def get_duckdb_connection(path: str | None = None):
    """Open (or create) a DuckDB database at the given path.

    Falls back to the DUCKDB_PATH environment variable, then to
    ``data/arlo.duckdb`` relative to the working directory.
    """
    path = path or os.environ.get("DUCKDB_PATH", "data/arlo.duckdb")
    return duckdb.connect(path)
