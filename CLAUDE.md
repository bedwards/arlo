# CLAUDE.md - Prediction Markets CLI

## Project Overview
CLI tool (`pmcli`) for trading on the two CFTC-regulated USD prediction markets with API access:
- **Kalshi** — REST API, RSA key pair auth, Python SDK (`kalshi-python`)
- **ForecastEx** — IBKR TWS API, requires TWS/IB Gateway running locally

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
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
# Kalshi
pmcli kalshi balance
pmcli kalshi positions
pmcli kalshi markets list --status open --limit 20
pmcli kalshi markets search "bitcoin"
pmcli kalshi markets detail TICKER
pmcli kalshi markets orderbook TICKER
pmcli kalshi buy TICKER --side yes --count 5 --price 45
pmcli kalshi orders
pmcli kalshi cancel ORDER_ID

# ForecastEx (Interactive Brokers)
pmcli fx balance
pmcli fx positions
pmcli fx buy SYMBOL --expiry 20260331 --strike 40500 --right C --count 10 --price 0.57
pmcli fx orders
pmcli fx cancel ORDER_ID
```

## Architecture
```
src/pmcli/
├── cli.py              # Click entry point, loads .env
├── config.py           # Config classes reading from env vars
├── display.py          # Shared output formatting (rich tables)
├── kalshi/
│   ├── client.py       # Wraps kalshi-python SDK
│   └── commands.py     # Click commands
└── forecastex/
    ├── client.py       # Wraps ibapi with threading
    └── commands.py     # Click commands
```

## Key Constraints
- **Kalshi**: Prices in cents (1-99), REST API with RSA-PSS signature auth
- **ForecastEx**: LMT orders only, BUY only (buy opposing contract to exit), contracts modeled as OPT (C=Yes, P=No), requires TWS/Gateway running
- Both exchanges: USD only, CFTC-regulated

## Conventions
- Client modules handle SDK init + auth + raw API calls
- Command modules handle Click decorators + user interaction + display
- All prices displayed as dollars to user; Kalshi internal prices in cents
- Order confirmation prompt before every trade execution
- Lazy imports in commands so missing credentials for one exchange don't break the other

## Dependencies
- `click` — CLI framework
- `python-dotenv` — .env loading
- `kalshi-python` — Official Kalshi SDK
- `ibapi` — Official IB TWS API
- `rich` — Terminal output formatting
