"""Configuration loading from env vars, .env, and TOML files."""
import os
from pathlib import Path

from pydantic import BaseModel, Field

try:
    import tomllib
except ImportError:
    import tomli as tomllib


# ---------- Pydantic Config Models ----------


class DatabaseConfig(BaseModel):
    postgres_url: str = Field(default="postgresql://localhost/arlo")
    duckdb_path: str = Field(default="data/arlo.duckdb")


class ClaudeConfig(BaseModel):
    api_key: str = Field(default="")
    model: str = Field(default="claude-opus-4-6")


class BraveSearchConfig(BaseModel):
    api_key: str = Field(default="")


class KalshiConfig(BaseModel):
    api_key_id: str = Field(default_factory=lambda: os.environ.get("KALSHI_API_KEY_ID", ""))
    private_key_path: str = Field(default_factory=lambda: os.environ.get("KALSHI_PRIVATE_KEY_PATH", ""))
    host: str = Field(default_factory=lambda: os.environ.get("KALSHI_API_HOST", "https://api.elections.kalshi.com/trade-api/v2"))

    @property
    def private_key_pem(self) -> str:
        with open(self.private_key_path) as f:
            return f.read()

    @property
    def is_demo(self) -> bool:
        return "demo" in self.host


class IBKRConfig(BaseModel):
    tws_host: str = Field(default_factory=lambda: os.environ.get("IB_TWS_HOST", "127.0.0.1"))
    tws_port: int = Field(default_factory=lambda: int(os.environ.get("IB_TWS_PORT", "7497")))
    client_id: int = Field(default_factory=lambda: int(os.environ.get("IB_CLIENT_ID", "1")))


# Backward compatibility alias
ForecastExConfig = IBKRConfig


class IngestConfig(BaseModel):
    chunk_size: int = Field(default=2000)
    chunk_overlap: int = Field(default=200)
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)


class TradeConfig(BaseModel):
    bankroll: float = Field(default=1000.0)
    max_position_pct: float = Field(default=0.05)
    max_exposure_pct: float = Field(default=0.30)
    kelly_fraction: float = Field(default=0.25)
    daily_loss_limit_pct: float = Field(default=0.03)
    min_edge: float = Field(default=0.10)


class ArloConfig(BaseModel):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    brave_search: BraveSearchConfig = Field(default_factory=BraveSearchConfig)
    kalshi: KalshiConfig = Field(default_factory=KalshiConfig)
    ibkr: IBKRConfig = Field(default_factory=IBKRConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    trade: TradeConfig = Field(default_factory=TradeConfig)


# ---------- Loading ----------


def _load_toml(path: str | Path) -> dict:
    """Load a TOML file, returning empty dict if not found."""
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)


def load_config(
    settings_path: str = "config/settings.toml",
    credentials_path: str = "config/credentials.toml",
) -> ArloConfig:
    """Load config from TOML files, with env var overrides."""
    settings = _load_toml(settings_path)
    credentials = _load_toml(credentials_path)

    # Merge settings and credentials
    merged = {**settings}
    for key, val in credentials.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = {**merged[key], **val}
        else:
            merged[key] = val

    # Env var overrides
    env_overrides = {
        "database": {"postgres_url": os.environ.get("DATABASE_URL")},
        "claude": {"api_key": os.environ.get("ANTHROPIC_API_KEY")},
        "brave_search": {"api_key": os.environ.get("BRAVE_SEARCH_API_KEY")},
        "kalshi": {
            "api_key_id": os.environ.get("KALSHI_API_KEY_ID"),
            "private_key_path": os.environ.get("KALSHI_PRIVATE_KEY_PATH"),
            "host": os.environ.get("KALSHI_API_HOST"),
        },
        "ibkr": {
            "tws_host": os.environ.get("IB_TWS_HOST"),
            "tws_port": int(os.environ.get("IB_TWS_PORT", "0")) or None,
            "client_id": int(os.environ.get("IB_CLIENT_ID", "0")) or None,
        },
    }

    # Apply non-None env overrides
    for section, overrides in env_overrides.items():
        if section not in merged:
            merged[section] = {}
        for key, val in overrides.items():
            if val is not None:
                merged[section][key] = val

    return ArloConfig(**merged)


# ---------- Singleton ----------

_config: ArloConfig | None = None


def get_config() -> ArloConfig:
    """Get the global config singleton."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
