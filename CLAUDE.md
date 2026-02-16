# CLAUDE.md - Arlo: AI Superforecasting System

## Project Overview
**Arlo** is a competitive AI superforecasting system for analysis, navigation, discovery, research, and action. It operates as a 7-stage pipeline: Ingest, Discover, Question, Forecast, Trade, Publish, Learn.

Trading is executed on the two CFTC-regulated USD prediction markets with API access:
- **Kalshi** — REST API, RSA key pair auth, Python SDK (`kalshi-python`)
- **ForecastEx** — IBKR TWS API, requires TWS/IB Gateway running locally

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
cp .env.example .env  # Edit with real credentials
pip install -e ".[dev]"
```

### Kalshi Credentials
1. Go to https://kalshi.com/account/profile → API Keys section
2. Create New API Key → save private key PEM file immediately (cannot retrieve later)
3. Set `KALSHI_API_KEY_ID` and `KALSHI_PRIVATE_KEY_PATH` in `.env`
4. Demo API available at `https://demo-api.kalshi.co/trade-api/v2`

### ForecastEx (IBKR) Credentials
1. Have an Interactive Brokers account with ForecastTrader enabled
2. Run TWS or IB Gateway locally (default port 7497 for TWS, 4001 for Gateway)
3. Enable API connections in TWS: Edit → Global Configuration → API → Settings
4. Set `IB_TWS_HOST`, `IB_TWS_PORT`, `IB_CLIENT_ID` in `.env`

## Usage
```bash
arlo status               # System status check
```

## Architecture
```
src/arlo/
├── __init__.py
├── cli.py                  # Typer CLI entry point
├── config.py               # Configuration from env vars and TOML files
├── db/
│   ├── postgres.py         # PostgreSQL + pgvector connection
│   ├── duckdb_conn.py      # DuckDB analytical queries
│   └── migrations/         # Alembic migration files
├── ingest/
│   ├── pipeline.py         # Main ingestion orchestrator
│   ├── youtube.py          # yt-dlp transcript extraction
│   ├── substack.py         # RSS + Playwright scraping
│   ├── news.py             # RSS feeds + Brave Search
│   ├── markets.py          # Prediction market data (Metaculus, Kalshi, etc.)
│   ├── economic.py         # FRED, World Bank, BLS, Census
│   ├── academic.py         # arXiv RSS
│   └── embedder.py         # sentence-transformers embedding pipeline
├── discover/
│   ├── topic_model.py      # HDBSCAN temporal topic clustering
│   ├── naive_observer.py   # Van Riper protocol via Claude
│   ├── oscillation.py      # Neustadt-May temporal oscillation
│   ├── five_whys.py        # Toyota Five Whys via Claude
│   ├── cross_domain.py     # NetworkX graph collision detection
│   └── domain_report.py    # Aggregate discovery outputs
├── question/
│   ├── operationalize.py   # Raw → operationalized forecasting questions
│   ├── cluster.py          # Bayesian Question Clustering
│   ├── novelty.py          # Check against existing markets
│   └── prioritize.py       # Rank by information value
├── forecast/
│   ├── engine.py           # Ensemble orchestrator
│   ├── claude_deep.py      # Claude deep research forecaster
│   ├── claude_adversary.py # Claude adversarial challenger
│   ├── market_implied.py   # Prediction market probability aggregator
│   ├── base_rate.py        # Historical base rate engine
│   ├── time_series.py      # statsforecast models
│   ├── aggregate.py        # Weighted aggregation + extremization
│   └── calibrate.py        # Platt scaling, isotonic regression
├── trade/
│   ├── edge_detector.py    # Identify forecast-vs-market divergences
│   ├── kelly.py            # Kelly criterion position sizing
│   ├── kalshi_client.py    # Kalshi API trading (migrated from pmcli)
│   ├── ibkr_client.py      # TWS API for ForecastEx (migrated from pmcli)
│   ├── risk.py             # Risk management rules
│   └── portfolio.py        # Position tracking and P&L
├── publish/
│   ├── charts.py           # Altair + Plotly chart generation
│   ├── essay.py            # Claude essay generation
│   └── export.py           # Markdown + image export
├── learn/
│   ├── scoring.py          # Brier and log score computation
│   ├── calibration.py      # Calibration analysis
│   ├── weights.py          # Component weight optimization
│   ├── bias_audit.py       # Claude-powered bias detection
│   └── backtest.py         # Historical backtesting framework
└── shared/
    ├── display.py          # Rich terminal output formatting
    ├── claude_api.py       # Claude Opus API interface
    ├── brave_search.py     # Brave Search API client
    └── prompts/            # Prompt templates as .txt files
```

## Key Constraints
- **Kalshi**: Prices in cents (1-99), REST API with RSA-PSS signature auth
- **ForecastEx**: LMT orders only, BUY only (buy opposing contract to exit), contracts modeled as OPT (C=Yes, P=No), requires TWS/Gateway running
- Both exchanges: USD only, CFTC-regulated
- **No local LLMs**: All LLM work uses Claude API via Anthropic SDK
- **Embeddings**: sentence-transformers (not Ollama)

## Conventions
- Client modules handle SDK init + auth + raw API calls
- Command modules handle Typer decorators + user interaction + display
- All prices displayed as dollars to user; Kalshi internal prices in cents
- Order confirmation prompt before every trade execution
- Lazy imports in commands so missing credentials for one exchange don't break the other
- Stub modules contain a single docstring until implemented

## Dependencies
- `typer` — CLI framework
- `rich` — Terminal output formatting
- `python-dotenv` — .env loading
- `anthropic` — Claude API
- `kalshi-python` — Official Kalshi SDK
- `ibapi` — Official IB TWS API (manual install)
- `sentence-transformers` — Local embeddings
- `polars` / `pandas` — Data processing
- `altair` / `plotly` — Visualization
- `psycopg` / `pgvector` / `duckdb` — Databases
- `sqlalchemy` / `alembic` — ORM and migrations
- `playwright` / `beautifulsoup4` / `feedparser` — Web scraping
- `statsforecast` — Time series models
- `scikit-learn` / `hdbscan` / `networkx` / `pgmpy` — ML / NLP
