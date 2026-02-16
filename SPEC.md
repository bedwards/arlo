Implement the full pipeline.

DO NOT DOWNGRADE/TRADE-OFF. STOP IF YOU NEED MY HELP. BUT WHEN YOU CAN MOVE ONTO OTHER PARTS OF THE SYSTEM AND COMPLETE THOSE AND THEN STOP AND REPORT TO ME WHEN YOU ARE TRULY BLOCKED.

Apply the full pipeline to.

The topic:

- Education
- US education
- Public education
- Texas education
- Waco Texas education
- Waco Texas ISD

Sources:

- Find your own
- Substack (use /feed URL once you discover the publication, e.g. https://dgardner.substack.com/feed )
- YouTube (download transcript once you find the video)
- Project Gutenberg
- The Internet Archive
- US census data
- The Texas Tribune https://www.texastribune.org/

DO NOT DOWNGRADE/TRADE-OFF. STOP IF YOU NEED MY HELP.


# CASSANDRA: Competitive AI Superforecasting System for Analysis, Navigation, Discovery, Research, and Action

## System Specification for Claude Code / Claude Opus 4.6 Implementation

**Version:** 1.0  
**Author:** Brian Edwards  
**Platform:** Mac Studio (Apple Silicon), Claude Max subscription  
**Date:** February 2026  

---

## 1. VISION & PHILOSOPHY

This system is not an analytics dashboard. It is not a chatbot with access to data. It is a **prediction engine** that begins upstream of where every other system begins — at the stage of **identifying what questions are not being asked**.

The article by Dan Gardner (PastPresentFuture, Feb 15 2026) crystallizes the thesis: in a world where AI delivers superforecaster-tier answers, **the bottleneck shifts to questions**. Cassandra's primary innovation is that it starts from raw signal — YouTube transcripts, Substack posts, news feeds, academic papers, podcasts, government filings — and applies structured epistemic techniques (Five Whys, Neustadt-May oscillation, Van Riper naive questioning, radical curiosity, design thinking) to **surface the questions nobody is asking yet**. Only then does it forecast. Only then does it act.

The system operates as a pipeline with seven stages, each implemented as a distinct subsystem with its own tooling, data stores, and Claude Opus 4.6 interface patterns.

### Core Principles

1. **Questions before answers.** The system's most valuable output is not a probability — it is the question that nobody else thought to ask.
2. **Prediction, not analysis.** Every output is oriented toward the future. Historical data exists to calibrate forecasts, not to produce retrospectives.
3. **Epistemic humility encoded in architecture.** The system assumes its own ignorance. Every pipeline stage explicitly models uncertainty. Brier scores are tracked and displayed for every prediction.
4. **Reflexivity awareness.** When Cassandra identifies a tradeable edge, it models whether that edge will be arbitraged away by the time it acts.
5. **Human-in-the-loop for irreversible actions.** Cassandra surfaces trades, but Brian confirms them. Cassandra drafts essays, but Brian publishes them.

---

## 2. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                        CASSANDRA SYSTEM                         │
│                     Mac Studio (Apple Silicon)                   │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ STAGE 1  │→ │ STAGE 2  │→ │ STAGE 3  │→ │ STAGE 4  │       │
│  │ INGEST   │  │ DISCOVER │  │ QUESTION │  │ FORECAST │       │
│  │          │  │          │  │          │  │          │       │
│  │ Signals  │  │ Domains  │  │ Generate │  │ Predict  │       │
│  │ & Sources│  │ & Gaps   │  │ & Refine │  │ & Score  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│       │                                          │              │
│       ▼                                          ▼              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│  │ STAGE 5  │→ │ STAGE 6  │→ │ STAGE 7  │                     │
│  │ TRADE    │  │ PUBLISH  │  │ LEARN    │                     │
│  │          │  │          │  │          │                     │
│  │ Kalshi   │  │ Essays   │  │ Calibra- │                     │
│  │ IBKR/FEX │  │ & Charts │  │ tion     │                     │
│  └──────────┘  └──────────┘  └──────────┘                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    SHARED INFRASTRUCTURE                  │   │
│  │  PostgreSQL │ Ollama │ Claude API │ Cron │ Git │ DuckDB  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack (All Free / Open Source / Free Tier)

| Component | Technology | License/Cost |
|-----------|-----------|--------------|
| Primary LLM | Claude Opus 4.6 via Claude Max subscription (already owned) | Included |
| Local LLM (batch/background) | Ollama + qwen2.5-coder:32b, llama3.3:70b | Free/Open |
| Orchestration | Python 3.12+ | Free |
| Task scheduling | `crontab` + custom Python scheduler | Free |
| Database (structured) | PostgreSQL 16 (Homebrew) | Free |
| Database (analytical) | DuckDB (embedded) | Free |
| Data processing | Polars | Free |
| Visualization | Altair + Plotly + Vega-Lite | Free |
| Web scraping | Playwright (headless Chromium) + BeautifulSoup4 | Free |
| YouTube transcripts | `yt-dlp` + `whisper.cpp` (local) or YouTube captions API | Free |
| RSS/Atom feeds | `feedparser` | Free |
| Substack scraping | Custom Playwright scraper | Free |
| PDF extraction | `pymupdf` (fitz) | Free |
| NLP/Embeddings | `sentence-transformers` (local) via Ollama embeddings | Free |
| Vector search | `pgvector` extension for PostgreSQL | Free |
| Prediction markets data | Kalshi public API (free, no auth for reads) | Free |
| Prediction markets data | Metaculus public API | Free |
| Prediction markets data | Polymarket public API | Free |
| Prediction markets data | Manifold Markets API | Free |
| Trading execution | Kalshi API (free, requires account) | Free |
| Trading execution | IBKR TWS API (free with IBKR account) | Free |
| Bulk data downloads | World Bank, FRED, UN, OECD, Our World in Data | Free |
| News/search | Brave Search API (free tier: 2000 queries/month) | Free |
| Essay publishing | Markdown → Substack (manual or API) | Free |
| Charts | `altair` + `vl-convert-python` (static export) | Free |
| Version control | Git + GitHub | Free |
| Process management | `supervisord` or `launchd` | Free |
| CLI interface | `typer` + `rich` | Free |

---

## 3. STAGE 1: INGEST — Signal Acquisition & Processing

### 3.1 Purpose

Continuously ingest raw signal from diverse sources. This is the "eyes and ears" of the system — the firehose of human discourse from which questions will eventually be extracted.

### 3.2 Source Types

#### 3.2.1 YouTube Transcripts
- **Tool:** `yt-dlp` for caption extraction; `whisper.cpp` (Apple Silicon MLX build) for channels without captions
- **Channels monitored:** Configurable list stored in `sources.toml`
- **Frequency:** Daily check for new videos on subscribed channels
- **Storage:** Raw transcript text + metadata (channel, title, date, URL, duration) in PostgreSQL `transcripts` table
- **Processing:** Chunk into 2000-token segments with 200-token overlap; generate embeddings via Ollama `nomic-embed-text`; store in `pgvector`

#### 3.2.2 Substack Posts
- **Tool:** RSS feeds where available; Playwright headless scraper for paywalled content the user subscribes to
- **Publications monitored:** Configurable list in `sources.toml`
- **Frequency:** Every 6 hours
- **Storage:** Full text + metadata in PostgreSQL `articles` table
- **Processing:** Same chunking and embedding pipeline as transcripts

#### 3.2.3 News Feeds
- **Tool:** `feedparser` for RSS/Atom; Brave Search API for keyword monitoring
- **Sources:** Reuters, AP, BBC, FT (headlines only unless subscribed), The Economist, The Atlantic, Nikkei Asia, Al Jazeera, South China Morning Post
- **Frequency:** Every 2 hours
- **Storage:** Headlines, summaries, and full text where available

#### 3.2.4 Government & Institutional Data
- **Sources:**
  - FRED (Federal Reserve Economic Data) — bulk CSV downloads + API
  - World Bank Development Indicators — bulk CSV
  - UN Data — bulk CSV
  - OECD — bulk CSV
  - Our World in Data — GitHub CSV repository
  - BLS (Bureau of Labor Statistics) — API
  - Census Bureau — API
  - SEC EDGAR — XBRL filings
- **Frequency:** Weekly bulk refresh; daily for FRED and BLS
- **Storage:** DuckDB for analytical queries; PostgreSQL for metadata

#### 3.2.5 Prediction Market Data
- **Sources:**
  - Metaculus API — all open questions, community predictions, resolution history
  - Kalshi API — all markets, orderbooks, historical prices
  - Polymarket API — all markets (read-only, no trading from US)
  - Manifold Markets API — all markets
  - ForecastEx (via IBKR) — available contracts
- **Frequency:** Every 30 minutes for prices; daily for new markets/questions
- **Storage:** PostgreSQL `markets` table with time-series price history

#### 3.2.6 Academic Preprints
- **Sources:** arXiv (RSS for selected categories: cs.AI, cs.CL, econ, q-fin, stat)
- **Frequency:** Daily
- **Storage:** Abstracts + metadata; full PDF downloaded on relevance trigger

### 3.3 Ingestion Pipeline Architecture

```python
# Pseudocode for ingestion pipeline
class IngestionPipeline:
    def __init__(self):
        self.sources = load_toml("sources.toml")
        self.db = PostgresConnection()
        self.embedder = OllamaEmbedder("nomic-embed-text")
        self.vectorstore = PGVector(self.db)
    
    async def ingest_source(self, source: Source) -> list[Document]:
        """Fetch, parse, chunk, embed, store."""
        raw = await source.fetch()
        documents = source.parse(raw)
        for doc in documents:
            chunks = chunk_text(doc.text, size=2000, overlap=200)
            embeddings = self.embedder.embed_batch(chunks)
            self.db.store_document(doc)
            self.vectorstore.store_chunks(doc.id, chunks, embeddings)
        return documents
    
    async def run_cycle(self):
        """Run all sources according to their schedules."""
        for source in self.sources:
            if source.is_due():
                await self.ingest_source(source)
```

### 3.4 Data Schema (PostgreSQL)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL, -- youtube, substack, rss, api, bulk_csv
    config JSONB NOT NULL,     -- URL, credentials, schedule
    last_fetched TIMESTAMPTZ,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    external_id TEXT,          -- YouTube video ID, article slug, etc.
    title TEXT,
    author TEXT,
    published_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    url TEXT,
    full_text TEXT,
    metadata JSONB
);

CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_index INTEGER,
    text TEXT NOT NULL,
    embedding vector(768),     -- nomic-embed-text dimension
    token_count INTEGER
);

CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE market_snapshots (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,    -- metaculus, kalshi, polymarket, manifold, forecastex
    market_id TEXT NOT NULL,
    title TEXT,
    question_text TEXT,
    current_probability FLOAT,
    volume FLOAT,
    close_date TIMESTAMPTZ,
    resolution TEXT,           -- NULL if unresolved
    snapshot_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE economic_series (
    series_id TEXT NOT NULL,
    source TEXT NOT NULL,       -- fred, worldbank, bls, etc.
    date DATE NOT NULL,
    value FLOAT,
    PRIMARY KEY (series_id, source, date)
);
```

---

## 4. STAGE 2: DISCOVER — Domain Identification & Gap Analysis

### 4.1 Purpose

This is where Cassandra diverges from every other forecasting system. Instead of starting with a pre-defined set of questions, Stage 2 analyzes the ingested signal to identify:

1. **Emerging domains** — topic clusters that are gaining attention disproportionate to their prior baseline
2. **Attention gaps** — important domains that are *under-discussed* relative to their potential impact
3. **Narrative shifts** — changes in how topics are framed that may signal inflection points
4. **Cross-domain connections** — links between seemingly unrelated domains that nobody is drawing

### 4.2 Techniques

#### 4.2.1 Temporal Topic Modeling
- Embed all recent documents (last 30 days) using `nomic-embed-text`
- Cluster with HDBSCAN (via `scikit-learn`) to identify topic clusters
- Compare cluster sizes and densities against 90-day and 365-day baselines
- Flag clusters that are growing >2σ faster than baseline (emerging) or shrinking while still high-impact (attention gaps)

#### 4.2.2 Claude Opus 4.6 — "Naive Observer" Protocol

This is the Van Riper technique encoded as a prompt protocol:

```
SYSTEM: You are an intelligent observer who knows NOTHING about current events. 
You have been presented with a large collection of recent transcripts, articles, 
and data from the past 7 days. 

Your task is to act like a four-year-old encountering the world for the first time.
Ask "why?" repeatedly. Assume nothing. Question everything.

For each topic cluster you identify:
1. What is this about? (Describe as if explaining to someone from 1950)
2. Why is this happening now? What changed?
3. Why does it matter? Who is affected?
4. What is NOT being discussed that should be?
5. What connections to other topics is everyone missing?
6. What assumptions are people making that might be wrong?

Do NOT propose solutions or actions. Only ask questions. The more naive and 
fundamental, the better.
```

#### 4.2.3 Neustadt-May Oscillation Protocol

For each emerging domain, Claude executes temporal oscillation:

```
SYSTEM: You are applying the Neustadt-May "Thinking In Time" framework.

Given: [DOMAIN DESCRIPTION + KEY DOCUMENTS]

Step 1 — PRESENT: "What's the situation?" Describe what is happening now, 
stripped of all interpretation and spin. Just facts.

Step 2 — PAST: "How did this come to be?" Trace the causal chain backwards. 
When did the current situation become inevitable? What were the key 
decision points? What historical analogies apply — and which are misleading?

Step 3 — FUTURE: Based on the trajectory from past to present, what are the 
plausible futures? Not what you hope or fear — what the evidence supports.

Step 4 — Return to PRESENT: Given what you now understand about past and 
future, what aspects of the present situation are you seeing differently?

Step 5 — QUESTIONS: What questions does this oscillation raise that nobody 
is asking?
```

#### 4.2.4 Five Whys Engine

For each identified signal, apply Toyota's Five Whys:

```
Input: "Rare earth export restrictions from China are tightening"

Why 1: Why are export restrictions tightening?
→ China controls ~60% of rare earth mining and ~90% of processing

Why 2: Why does China control so much of the processing?
→ Western nations offshored processing in the 1990s-2000s due to 
   environmental costs and cheap Chinese labor

Why 3: Why didn't Western nations maintain strategic reserves or 
       alternative supply chains?
→ Rare earths were not classified as strategically critical until 
   the 2010 dispute with Japan

Why 4: Why has diversification been so slow since 2010?
→ New mines take 10-15 years to develop; processing facilities 
   require massive capital; environmental permitting is complex

Why 5: Why hasn't the urgency matched the timeline?
→ QUESTION SURFACES: "Are Western governments systematically 
   underestimating the speed at which China can weaponize rare 
   earth dependencies relative to the speed at which alternatives 
   can be developed?"
```

#### 4.2.5 Cross-Domain Collision Detection

- Maintain a graph database (NetworkX in Python, persisted to PostgreSQL) of entities and relationships extracted from documents
- Identify nodes that bridge otherwise disconnected clusters
- These bridging entities often reveal the questions nobody is asking because they sit at the intersection of siloed expertise

### 4.3 Output

Stage 2 produces a ranked list of **Domain Reports**, each containing:
- Domain name and description
- Key documents and sources
- Attention trajectory (rising/falling/gap)
- Historical context (Neustadt-May)
- Five Whys analysis
- Cross-domain connections
- **Candidate questions** (unrefined — Stage 3 will operationalize these)

Storage: PostgreSQL `domains` and `domain_questions_raw` tables.

---

## 5. STAGE 3: QUESTION — Generation, Operationalization & Refinement

### 5.1 Purpose

Transform the raw, naive questions from Stage 2 into **operationalized forecasting questions** — questions with clear resolution criteria, timeframes, and measurable outcomes.

This is the critical translation step. A question like "Are Western governments underestimating rare earth vulnerability?" is important but unforecastable. Stage 3 transforms it into:

- "Will the US Department of Defense issue a rare earth supply chain emergency declaration before January 1, 2027?" (Binary, resolvable)
- "What will be the price of neodymium oxide per kg on December 31, 2026?" (Numeric, resolvable)
- "Will China announce new export restrictions on any rare earth element before July 1, 2026?" (Binary, resolvable)

### 5.2 Question Operationalization Protocol

```
SYSTEM: You are an expert at transforming vague concerns into precise, 
resolvable forecasting questions in the style of Metaculus and Good Judgment.

Given a raw question or concern, generate 3-7 operationalized forecasting 
questions. Each must have:

1. QUESTION TEXT: Clear, unambiguous yes/no or numeric question
2. RESOLUTION CRITERIA: Exactly how this resolves, citing specific data 
   sources (e.g., "Resolves YES if the BLS CPI-U year-over-year change 
   exceeds 4.0% for the December 2026 release")
3. TIMEFRAME: Specific close date
4. BASE RATE: Historical frequency of similar events, if available
5. CURRENT MARKET PRICE: What Metaculus/Kalshi/Polymarket say, if a 
   similar question exists
6. INFORMATION VALUE: How much would knowing the answer change decisions? 
   (High/Medium/Low)
7. TRADEABILITY: Can this be traded on Kalshi or ForecastEx? If so, 
   which contract?

Prefer questions that are:
- Not already being asked on major platforms (novel questions have the 
  highest marginal value)
- Answerable within 3-18 months (the superforecaster sweet spot)
- Connected to actionable decisions
- Amenable to being decomposed into sub-questions (Bayesian Question 
  Clustering per Tetlock)
```

### 5.3 Bayesian Question Clustering

For each high-level question, decompose into a tree of sub-questions where the answers to sub-questions provide evidence for the parent:

```
Parent: "Will the US enter a recession in 2026?"
├── "Will unemployment exceed 5% before Dec 2026?" (BLS data)
├── "Will the yield curve remain inverted for >18 months?" (FRED data)
├── "Will consumer spending growth turn negative?" (BEA data)
├── "Will the Fed cut rates by >100bp before Dec 2026?" (FRED + Kalshi)
└── "Will a major bank fail in 2026?" (FDIC data)
```

Each sub-question gets its own forecast, and the parent forecast is computed as a weighted combination using a Bayesian network (implemented with `pgmpy` or custom).

### 5.4 Novelty Detection

Before adding a question to the active set, check:
1. **Metaculus API:** Does a similar question already exist? (Semantic search against Metaculus question corpus)
2. **Kalshi/ForecastEx:** Is there an existing contract? (API search)
3. **Polymarket/Manifold:** Similar market exists?

If yes: import the existing market's probability as a prior. Flag as "market-tracked."
If no: flag as **"novel question"** — these are Cassandra's highest-value outputs.

### 5.5 Output

Stage 3 produces **Operationalized Question Sets**, stored in:

```sql
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER REFERENCES domains(id),
    parent_question_id INTEGER REFERENCES questions(id), -- for BCQ trees
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,    -- binary, numeric, date, multiple_choice
    resolution_criteria TEXT NOT NULL,
    resolution_source TEXT,         -- specific URL or data source
    open_date DATE NOT NULL,
    close_date DATE NOT NULL,
    base_rate FLOAT,
    is_novel BOOLEAN DEFAULT FALSE,
    information_value TEXT,         -- high, medium, low
    tradeable_on JSONB,            -- {"kalshi": "TICKER", "forecastex": "SYMBOL"}
    status TEXT DEFAULT 'active',   -- active, resolved_yes, resolved_no, voided
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. STAGE 4: FORECAST — Prediction Engine

### 6.1 Purpose

Generate calibrated probabilistic forecasts for each operationalized question. This is where Cassandra competes with Mantic and Good Judgment's Superforecasters.

### 6.2 Forecasting Architecture

Cassandra uses an **ensemble of diverse forecasting approaches**, then aggregates and extremizes in the style of the Good Judgment Project's winning algorithm.

#### 6.2.1 Component Forecasters

**Forecaster A: Claude Opus 4.6 — Deep Research Agent**
- For each question, Claude performs multi-step research:
  1. Retrieve relevant chunks from the vector store (pgvector similarity search)
  2. Search Brave Search API for current information
  3. Retrieve relevant prediction market prices
  4. Retrieve relevant economic time series from DuckDB
  5. Synthesize into a structured analysis with explicit probability estimate
- Prompt template encodes superforecaster best practices:
  - Start with the base rate (outside view)
  - Adjust based on specific evidence (inside view)
  - Consider the status quo bias (most things don't change)
  - Assign granular probabilities (not round numbers)
  - Explicitly consider the strongest argument against your estimate

**Forecaster B: Claude Opus 4.6 — Adversarial Challenger**
- Same question, same data access, but prompted to challenge Forecaster A:
  - "What is Forecaster A most likely getting wrong?"
  - "What evidence is Forecaster A underweighting?"
  - "What base rate is Forecaster A ignoring?"
- Produces an independent probability estimate

**Forecaster C: Local LLM (Ollama — llama3.3:70b) — Cheap Diverse Perspective**
- Lower-cost forecaster that provides diversity
- Given a simplified brief (no deep research, just the question + key context)
- 5 independent runs, median taken

**Forecaster D: Market-Implied Probability**
- For questions with existing prediction market contracts:
  - Kalshi price / 100 = probability
  - Metaculus community prediction
  - Polymarket price
  - Manifold probability
- Aggregate across platforms using inverse-variance weighting

**Forecaster E: Base Rate Engine**
- Statistical model based purely on historical base rates
- For each question type, compute:
  - How often has this type of event occurred historically?
  - What is the trend?
  - What is the seasonal pattern?
- Uses Polars for fast computation over DuckDB economic series

**Forecaster F: Time Series Model (when applicable)**
- For numeric questions with historical data (inflation, unemployment, etc.)
- Use `statsforecast` (Nixtla, free, MIT license) for:
  - AutoARIMA
  - AutoETS
  - AutoCES
- Convert point forecasts to probability distributions

#### 6.2.2 Aggregation Algorithm

Following the GJP literature:

1. **Collect** all component forecasts: `[pA, pB, pC, pD, pE, pF]`
2. **Weight** by track record (initially equal, updated as forecasts resolve):
   ```python
   # Brier-score-weighted aggregation
   weights = [1/brier_score_i for i in forecasters]  # lower Brier = higher weight
   weights = normalize(weights)
   p_aggregate = sum(w * p for w, p in zip(weights, forecasts))
   ```
3. **Extremize** the aggregate (push toward 0 or 1):
   ```python
   # Extremization parameter d, calibrated on resolved questions
   # d > 1 extremizes; d = 1 is no change; d < 1 moderates
   from math import log, exp
   logodds = log(p_aggregate / (1 - p_aggregate))
   extremized_logodds = d * logodds
   p_final = 1 / (1 + exp(-extremized_logodds))
   ```
4. **Calibrate** using Platt scaling on historical predictions vs outcomes

### 6.3 Forecast Update Schedule

- **Daily:** Update all active forecasts when significant new information is detected (new documents matching question embeddings above cosine similarity threshold 0.8)
- **Weekly:** Full re-forecast of all active questions regardless of new information
- **On market movement:** If any tracked market moves >5 percentage points in a day, trigger immediate re-forecast

### 6.4 Output

```sql
CREATE TABLE forecasts (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    forecast_date TIMESTAMPTZ DEFAULT NOW(),
    probability FLOAT NOT NULL,       -- final aggregated probability
    confidence_interval_low FLOAT,    -- 10th percentile
    confidence_interval_high FLOAT,   -- 90th percentile
    components JSONB NOT NULL,        -- individual forecaster outputs
    aggregation_method TEXT,
    extremization_d FLOAT,
    reasoning_summary TEXT,           -- Claude-generated summary of key factors
    key_uncertainties TEXT[],          -- list of factors that could swing the forecast
    update_triggers TEXT[],           -- what would cause an update
    UNIQUE(question_id, forecast_date)
);

CREATE TABLE forecast_scores (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    forecast_id INTEGER REFERENCES forecasts(id),
    resolution_value FLOAT,           -- 1.0 for yes, 0.0 for no
    brier_score FLOAT,
    log_score FLOAT,
    resolved_at TIMESTAMPTZ
);
```

---

## 7. STAGE 5: TRADE — Prediction Market Execution

### 7.1 Purpose

When Cassandra's forecast diverges significantly from market prices, identify and execute trades on Kalshi and ForecastEx (via IBKR TWS API).

### 7.2 Edge Detection

```python
def detect_edge(cassandra_prob: float, market_prob: float, 
                market: str, volume: float) -> TradeSignal | None:
    """
    Identify tradeable edges.
    
    Rules:
    1. Minimum divergence: |cassandra - market| > 0.10 (10 percentage points)
    2. Minimum confidence: cassandra's confidence interval must not overlap 
       with market price
    3. Minimum volume: market must have >$1000 daily volume (liquidity check)
    4. Reflexivity check: Is this edge likely to persist? 
       (Novel questions: yes. Heavily traded questions: probably not.)
    5. Kelly criterion position sizing (fractional Kelly at 25%)
    """
    divergence = cassandra_prob - market_prob
    if abs(divergence) < 0.10:
        return None
    
    # Kelly criterion for binary events
    # f* = (bp - q) / b where b = odds, p = true prob, q = 1-p
    if divergence > 0:  # Cassandra says more likely than market
        b = (1 / market_prob) - 1  # implied odds of buying YES
        f_star = (b * cassandra_prob - (1 - cassandra_prob)) / b
    else:  # Cassandra says less likely
        b = (1 / (1 - market_prob)) - 1  # implied odds of buying NO
        f_star = (b * (1 - cassandra_prob) - cassandra_prob) / b
    
    if f_star <= 0:
        return None
    
    fraction_kelly = 0.25  # conservative
    position_size = f_star * fraction_kelly * bankroll
    
    return TradeSignal(
        direction="YES" if divergence > 0 else "NO",
        size=position_size,
        edge=abs(divergence),
        kelly_fraction=f_star,
    )
```

### 7.3 Kalshi Trading Integration

```python
import requests

class KalshiTrader:
    BASE_URL = "https://trading-api.kalshi.com/trade-api/v2"
    
    def __init__(self, api_key_id: str, private_key_path: str):
        self.api_key_id = api_key_id
        self.private_key = load_private_key(private_key_path)
    
    def get_markets(self, series_ticker: str) -> list[dict]:
        """Fetch all markets for a series."""
        resp = requests.get(f"{self.BASE_URL}/markets", 
                           params={"series_ticker": series_ticker})
        return resp.json()["markets"]
    
    def place_order(self, ticker: str, side: str, yes_price: int, 
                    count: int) -> dict:
        """Place a limit order. REQUIRES HUMAN CONFIRMATION."""
        # This is called only after Brian confirms via CLI prompt
        order = {
            "ticker": ticker,
            "action": "buy",
            "side": side,  # "yes" or "no"
            "type": "limit",
            "yes_price": yes_price,  # in cents
            "count": count,
        }
        resp = self.authenticated_post(f"{self.BASE_URL}/portfolio/orders", 
                                        json=order)
        return resp.json()
```

### 7.4 IBKR/ForecastEx Trading Integration

```python
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

class ForecastExTrader(EWrapper, EClient):
    """
    TWS API client for ForecastEx contracts.
    
    ForecastEx contracts are modeled as options in the TWS API:
    - Exchange: "FORECASTEX"
    - Currency: "USD"
    - SecType: "OPT"
    - Right: "C" for YES, "P" for NO
    - Strike: the threshold value
    - LastTradeDateOrContractMonth: YYYYMMDD
    """
    
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id = None
    
    def build_forecast_contract(self, symbol: str, expiry: str, 
                                 right: str, strike: float) -> Contract:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"
        contract.exchange = "FORECASTEX"
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = expiry
        contract.right = right  # "C" for YES, "P" for NO
        contract.strike = strike
        return contract
    
    def place_forecast_order(self, contract: Contract, action: str,
                              quantity: int, limit_price: float) -> int:
        """Place order. REQUIRES HUMAN CONFIRMATION."""
        order = Order()
        order.action = action  # "BUY"
        order.orderType = "LMT"
        order.totalQuantity = quantity
        order.lmtPrice = limit_price
        order.tif = "GTC"
        
        order_id = self.next_order_id
        self.placeOrder(order_id, contract, order)
        self.next_order_id += 1
        return order_id
```

### 7.5 Position Management

```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,        -- kalshi, forecastex
    market_id TEXT NOT NULL,
    question_id INTEGER REFERENCES questions(id),
    direction TEXT NOT NULL,        -- yes, no
    entry_price FLOAT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_date TIMESTAMPTZ DEFAULT NOW(),
    exit_price FLOAT,
    exit_date TIMESTAMPTZ,
    pnl FLOAT,
    cassandra_prob_at_entry FLOAT,
    market_prob_at_entry FLOAT,
    edge_at_entry FLOAT,
    status TEXT DEFAULT 'open'     -- open, closed, expired
);

CREATE TABLE trade_log (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES positions(id),
    action TEXT NOT NULL,           -- open, close, partial_close
    price FLOAT NOT NULL,
    quantity INTEGER NOT NULL,
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    human_confirmed BOOLEAN DEFAULT FALSE,
    confirmation_timestamp TIMESTAMPTZ
);
```

### 7.6 Risk Controls

- **Maximum position size:** 5% of bankroll per question
- **Maximum total exposure:** 30% of bankroll across all positions
- **Stop-loss:** Close position if Cassandra's forecast flips direction (i.e., bought YES but forecast now <50%)
- **Daily P&L limit:** Halt new trades if daily loss exceeds 3% of bankroll
- **Correlation check:** Limit exposure to correlated questions (e.g., multiple recession indicators)

---

## 8. STAGE 6: PUBLISH — Essay & Chart Generation

### 8.1 Purpose

Produce publication-quality essays with charts for Brian's Substacks, incorporating Cassandra's predictions, analysis, and the novel questions it has identified.

### 8.2 Chart Generation Pipeline

```python
import polars as pl
import altair as alt
import plotly.graph_objects as go

class ChartEngine:
    """
    Generate charts from Cassandra's data using Polars + Altair + Plotly.
    """
    
    def forecast_history_chart(self, question_id: int) -> alt.Chart:
        """
        Show how Cassandra's forecast evolved over time vs. market price.
        Altair for static Substack-ready SVG/PNG.
        """
        df = pl.read_database(
            f"""SELECT f.forecast_date, f.probability as cassandra,
                       m.current_probability as market
                FROM forecasts f
                LEFT JOIN market_snapshots m ON ...
                WHERE f.question_id = {question_id}
                ORDER BY f.forecast_date""",
            self.db_uri
        )
        
        base = alt.Chart(df.to_pandas()).encode(x='forecast_date:T')
        
        cassandra_line = base.mark_line(color='#e63946', strokeWidth=2).encode(
            y=alt.Y('cassandra:Q', title='Probability', scale=alt.Scale(domain=[0, 1]))
        )
        market_line = base.mark_line(color='#457b9d', strokeDash=[5,5]).encode(
            y='market:Q'
        )
        
        return (cassandra_line + market_line).properties(
            width=700, height=400,
            title='Cassandra vs. Market Probability'
        )
    
    def calibration_chart(self) -> alt.Chart:
        """
        Calibration plot: predicted probability vs. actual frequency.
        The gold standard for forecast quality.
        """
        df = pl.read_database("""
            SELECT 
                ROUND(f.probability * 10) / 10 as predicted_bucket,
                AVG(CASE WHEN q.status = 'resolved_yes' THEN 1.0 ELSE 0.0 END) as actual_freq,
                COUNT(*) as n
            FROM forecasts f
            JOIN questions q ON f.question_id = q.id
            WHERE q.status IN ('resolved_yes', 'resolved_no')
            GROUP BY predicted_bucket
        """, self.db_uri)
        
        perfect = alt.Chart(
            pl.DataFrame({"x": [0, 1], "y": [0, 1]}).to_pandas()
        ).mark_line(strokeDash=[3,3], color='gray').encode(x='x:Q', y='y:Q')
        
        calibration = alt.Chart(df.to_pandas()).mark_circle(size=100).encode(
            x=alt.X('predicted_bucket:Q', title='Predicted Probability'),
            y=alt.Y('actual_freq:Q', title='Actual Frequency'),
            size='n:Q'
        )
        
        return (perfect + calibration).properties(
            width=500, height=500,
            title='Cassandra Calibration Plot'
        )
    
    def plotly_interactive_dashboard(self, domain_id: int) -> go.Figure:
        """
        Plotly for interactive HTML dashboards (local viewing).
        """
        # Multi-panel figure with subplots for:
        # - Question tree visualization
        # - Forecast distributions
        # - Edge detection heatmap
        # - P&L tracking
        pass
    
    def export_for_substack(self, chart: alt.Chart, filename: str):
        """Export as PNG for Substack embedding."""
        chart.save(f"output/charts/{filename}.png", scale_factor=2)
        chart.save(f"output/charts/{filename}.svg")
```

### 8.3 Essay Generation Protocol

```
SYSTEM: You are writing an essay for Brian Edwards' Substack. 

Style: Modern literary nonfiction in the tradition of long-form journalism.
Not academic. Not dry. Not listicles. Think Dan Gardner meets Matt Levine 
meets Brian's own style — incisive, occasionally wry, always substantive.

Structure for a typical Cassandra essay:
1. HOOK: Open with the question nobody is asking (the Stage 2 output)
2. CONTEXT: What is everyone paying attention to instead? Why?
3. DISCOVERY: How Cassandra found this question. What naive questions led here.
4. EVIDENCE: Data, charts, historical analogies. Show the Five Whys chain.
5. FORECAST: Cassandra's probability estimate. What would change it.
6. IMPLICATIONS: What should you do if this forecast is right? What if wrong?
7. UNCERTAINTY: What Cassandra doesn't know. Where the forecast horizon lies.

Include chart references: [CHART: forecast_history_q42.png]
Include data references: cite specific sources, dates, numbers.

Length: 2000-4000 words.
Tone: Confident but epistemically humble. Show your work.
```

### 8.4 Output

- Markdown essays in `output/essays/`
- Charts in `output/charts/` (PNG and SVG)
- Combined HTML with inline charts for preview
- Ready for copy-paste to Substack or automated publishing via Substack API

---

## 9. STAGE 7: LEARN — Calibration, Backtesting & Self-Improvement

### 9.1 Purpose

Track prediction accuracy, update component weights, improve calibration, and identify systematic biases.

### 9.2 Scoring

For each resolved question:

```python
def brier_score(forecast: float, outcome: float) -> float:
    """Lower is better. 0 = perfect, 0.25 = coin flip, 1 = always wrong."""
    return (forecast - outcome) ** 2

def log_score(forecast: float, outcome: float) -> float:
    """More negative is worse. Heavily penalizes confident wrong predictions."""
    import math
    eps = 1e-10
    if outcome == 1:
        return math.log(max(forecast, eps))
    else:
        return math.log(max(1 - forecast, eps))
```

### 9.3 Calibration Analysis

Monthly automated report:
- Overall Brier score (target: <0.15 — superforecaster range)
- Calibration curve (perfect calibration = diagonal line)
- Per-domain performance breakdown
- Per-component forecaster performance
- Comparison vs. Metaculus community prediction on overlapping questions
- Comparison vs. prediction market prices at time of forecast

### 9.4 Component Weight Updates

After every 50 resolved questions, re-estimate optimal weights for the aggregation algorithm using logistic regression on historical forecasts.

### 9.5 Bias Detection

Claude Opus 4.6 reviews Cassandra's forecast history:

```
SYSTEM: You are auditing Cassandra's forecasting record. 

Review the last 100 resolved forecasts. Identify:
1. Systematic overconfidence or underconfidence in any domain
2. Recurring errors (e.g., consistently underestimating political instability)
3. Domains where Cassandra outperforms markets vs. underperforms
4. Questions where the Five Whys / naive questioning actually surfaced 
   important novel questions vs. where it produced noise
5. Recommendations for adjusting the pipeline
```

### 9.6 Backtesting Framework

For new techniques or prompt changes:

```python
class Backtester:
    """
    Replay historical questions with modified pipeline.
    
    Uses Metaculus resolved questions (API provides historical data).
    Constrains information access to before question close date.
    """
    
    def backtest(self, bot_config: dict, questions: list[Question],
                  cutoff_dates: list[datetime]) -> BacktestResult:
        results = []
        for question, cutoff in zip(questions, cutoff_dates):
            # Restrict search to before cutoff
            forecast = self.forecast_with_cutoff(bot_config, question, cutoff)
            score = brier_score(forecast, question.resolution)
            results.append(score)
        
        return BacktestResult(
            mean_brier=mean(results),
            calibration_curve=compute_calibration(results),
            n_questions=len(results)
        )
```

---

## 10. CLI INTERFACE

The entire system is operated via a CLI built with `typer` and `rich`:

```bash
# Run the full pipeline
cassandra run --stage all

# Run specific stages
cassandra ingest --source youtube --channel "@PBSnewshour"
cassandra discover --window 7d
cassandra question --domain "rare-earth-supply-chains"
cassandra forecast --question-id 42
cassandra forecast --all-active

# Interactive exploration
cassandra explore  # Rich TUI showing domains, questions, forecasts
cassandra ask "What questions should I be asking about semiconductor supply?"
cassandra why "Why is China restricting rare earth exports?"  # Five Whys

# Trading
cassandra scan-edges  # Show all questions where Cassandra disagrees with market
cassandra trade --question-id 42 --confirm  # Execute trade (with confirmation)
cassandra portfolio  # Show all positions, P&L

# Publishing
cassandra essay --domain "rare-earth-supply-chains" --output essay.md
cassandra chart --question-id 42 --type forecast-history

# Calibration
cassandra score  # Show overall Brier score and calibration
cassandra audit  # Run bias detection
cassandra backtest --config new_prompt.toml --questions metaculus-2024

# System
cassandra status  # Show ingestion status, database sizes, last run times
cassandra sources list
cassandra sources add --type youtube --url "https://youtube.com/@channel"
```

---

## 11. DIRECTORY STRUCTURE

```
cassandra/
├── README.md
├── pyproject.toml              # Project config, dependencies
├── cassandra/
│   ├── __init__.py
│   ├── cli.py                  # Typer CLI entry point
│   ├── config.py               # Load sources.toml, settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres.py         # PostgreSQL connection + migrations
│   │   ├── duckdb.py           # DuckDB analytical queries
│   │   └── migrations/         # SQL migration files
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── pipeline.py         # Main ingestion orchestrator
│   │   ├── youtube.py          # yt-dlp + whisper integration
│   │   ├── substack.py         # RSS + Playwright scraper
│   │   ├── news.py             # RSS feeds + Brave Search
│   │   ├── markets.py          # Metaculus, Kalshi, Polymarket, Manifold
│   │   ├── economic.py         # FRED, World Bank, BLS, etc.
│   │   ├── academic.py         # arXiv RSS
│   │   └── embedder.py         # Ollama embedding pipeline
│   ├── discover/
│   │   ├── __init__.py
│   │   ├── topic_model.py      # HDBSCAN clustering
│   │   ├── naive_observer.py   # Van Riper protocol via Claude
│   │   ├── oscillation.py      # Neustadt-May protocol via Claude
│   │   ├── five_whys.py        # Toyota Five Whys via Claude
│   │   ├── cross_domain.py     # NetworkX graph analysis
│   │   └── domain_report.py    # Aggregate outputs
│   ├── question/
│   │   ├── __init__.py
│   │   ├── operationalize.py   # Raw → operationalized questions
│   │   ├── cluster.py          # Bayesian Question Clustering
│   │   ├── novelty.py          # Check against existing markets
│   │   └── prioritize.py       # Rank by information value
│   ├── forecast/
│   │   ├── __init__.py
│   │   ├── engine.py           # Ensemble orchestrator
│   │   ├── claude_deep.py      # Claude deep research forecaster
│   │   ├── claude_adversary.py # Claude adversarial forecaster
│   │   ├── local_llm.py        # Ollama-based forecaster
│   │   ├── market_implied.py   # Prediction market aggregator
│   │   ├── base_rate.py        # Historical base rate engine
│   │   ├── time_series.py      # statsforecast models
│   │   ├── aggregate.py        # Weighted aggregation + extremization
│   │   └── calibrate.py        # Platt scaling, isotonic regression
│   ├── trade/
│   │   ├── __init__.py
│   │   ├── edge_detector.py    # Identify divergences
│   │   ├── kelly.py            # Position sizing
│   │   ├── kalshi_client.py    # Kalshi API trading
│   │   ├── ibkr_client.py      # TWS API for ForecastEx
│   │   ├── risk.py             # Risk management rules
│   │   └── portfolio.py        # Position tracking
│   ├── publish/
│   │   ├── __init__.py
│   │   ├── charts.py           # Altair + Plotly chart generation
│   │   ├── essay.py            # Claude essay generation
│   │   └── export.py           # Markdown + image export
│   ├── learn/
│   │   ├── __init__.py
│   │   ├── scoring.py          # Brier, log scores
│   │   ├── calibration.py      # Calibration analysis
│   │   ├── weights.py          # Component weight optimization
│   │   ├── bias_audit.py       # Claude-powered bias detection
│   │   └── backtest.py         # Historical backtesting framework
│   └── shared/
│       ├── __init__.py
│       ├── claude_api.py       # Claude Opus 4.6 interface (via Anthropic API)
│       ├── ollama_api.py       # Local LLM interface
│       ├── brave_search.py     # Brave Search API
│       └── prompts/            # All prompt templates as .txt files
│           ├── naive_observer.txt
│           ├── oscillation.txt
│           ├── five_whys.txt
│           ├── operationalize.txt
│           ├── forecast_deep.txt
│           ├── forecast_adversary.txt
│           ├── essay_template.txt
│           └── bias_audit.txt
├── config/
│   ├── sources.toml            # All data sources
│   ├── settings.toml           # System settings
│   └── credentials.toml        # API keys (git-ignored)
├── scripts/
│   ├── setup_db.sh             # Initialize PostgreSQL + pgvector
│   ├── setup_ollama.sh         # Pull required models
│   ├── download_bulk_data.sh   # Initial bulk data download
│   └── cron_setup.sh           # Install cron jobs
├── output/
│   ├── essays/
│   ├── charts/
│   └── reports/
├── tests/
│   ├── test_ingest.py
│   ├── test_discover.py
│   ├── test_question.py
│   ├── test_forecast.py
│   ├── test_trade.py
│   └── test_backtest.py
└── data/
    ├── bulk/                   # Downloaded CSV bulk data
    └── cache/                  # Embedding cache, search cache
```

---

## 12. DEPENDENCIES (pyproject.toml)

```toml
[project]
name = "cassandra"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    # Core
    "typer>=0.12",
    "rich>=13",
    "httpx>=0.27",
    "pydantic>=2.5",
    "tomli>=2.0",
    
    # Database
    "psycopg[binary]>=3.1",
    "pgvector>=0.3",
    "duckdb>=1.1",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    
    # Data processing
    "polars>=1.0",
    "pandas>=2.2",           # needed for Altair interop
    "numpy>=1.26",
    
    # Visualization
    "altair>=5.3",
    "vl-convert-python>=1.3",
    "plotly>=5.22",
    
    # NLP / ML
    "sentence-transformers>=3.0",
    "scikit-learn>=1.5",     # HDBSCAN
    "hdbscan>=0.8",
    "networkx>=3.3",
    "pgmpy>=0.0.1",          # Bayesian networks
    
    # Web / Scraping
    "playwright>=1.44",
    "beautifulsoup4>=4.12",
    "feedparser>=6.0",
    "yt-dlp>=2024.0",
    
    # Time series forecasting
    "statsforecast>=1.7",
    
    # APIs
    "anthropic>=0.34",        # Claude API
    "ollama>=0.3",            # Ollama Python client
    
    # Trading
    "ibapi>=10.19",           # IBKR TWS API
    
    # PDF
    "pymupdf>=1.24",
    
    # Utilities
    "python-dateutil>=2.9",
    "tenacity>=8.5",          # Retry logic
    "structlog>=24.0",        # Structured logging
    "apscheduler>=3.10",      # Scheduling
]
```

---

## 13. DEPLOYMENT & OPERATIONS

### 13.1 Mac Studio Setup

```bash
# Prerequisites
brew install postgresql@16 ollama
brew install --cask docker  # Optional, for isolated services

# PostgreSQL with pgvector
brew install pgvector
createdb cassandra
psql cassandra -c "CREATE EXTENSION vector;"

# Ollama models
ollama pull nomic-embed-text    # Embeddings (768d, fast)
ollama pull llama3.3:70b        # Diverse forecaster (runs on M-series)
ollama pull qwen2.5-coder:32b   # Code assistance

# Python environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Playwright browsers
playwright install chromium

# Bulk data initial download
./scripts/download_bulk_data.sh

# Database migrations
alembic upgrade head

# Whisper.cpp for local transcription (Apple Silicon optimized)
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp && make -j && cd ..
```

### 13.2 Cron Schedule

```cron
# Ingestion
*/30 * * * * cassandra ingest --source markets          # Every 30 min
0 */2 * * *  cassandra ingest --source news              # Every 2 hours
0 */6 * * *  cassandra ingest --source substack           # Every 6 hours
0 4 * * *    cassandra ingest --source youtube            # Daily at 4am
0 5 * * 0    cassandra ingest --source economic --full    # Weekly Sunday 5am

# Discovery & Questioning
0 6 * * *    cassandra discover --window 7d              # Daily at 6am
0 7 * * 1    cassandra question --from-discovery         # Weekly Monday 7am

# Forecasting
0 8 * * *    cassandra forecast --all-active             # Daily at 8am
0 9 * * *    cassandra scan-edges                         # Daily at 9am

# Learning
0 10 * * 0   cassandra score                              # Weekly Sunday 10am
0 11 1 * *   cassandra audit                              # Monthly 1st at 11am
```

### 13.3 Resource Estimates (Mac Studio M2 Ultra, 192GB RAM)

| Process | RAM | GPU | Disk | Notes |
|---------|-----|-----|------|-------|
| PostgreSQL + pgvector | 8-16 GB | — | 50 GB | Growing with document corpus |
| DuckDB | 2-4 GB | — | 20 GB | Economic time series |
| Ollama llama3.3:70b | 40-45 GB | Apple Neural Engine | 40 GB model | Runs well on M-series |
| Ollama nomic-embed-text | 0.5 GB | ANE | 0.3 GB model | Very fast |
| Ollama qwen2.5-coder:32b | 20 GB | ANE | 20 GB model | For code tasks |
| Whisper.cpp | 2 GB | ANE | 1.5 GB model | Only when transcribing |
| Python processes | 4-8 GB | — | — | Polars, HDBSCAN, etc. |
| **Total peak** | **~90 GB** | | **~130 GB** | Fits in 192GB with headroom |

---

## 14. WHAT MAKES THIS DIFFERENT

### 14.1 vs. Mantic

Mantic is a purpose-built AI forecasting engine with custom RL training on forecasting data. Cassandra cannot replicate that. What Cassandra does differently:

1. **Question generation is the primary output.** Mantic answers questions. Cassandra asks them first.
2. **Transparent reasoning chain.** Every forecast includes the full Five Whys, Neustadt-May oscillation, and naive questioning chain. Mantic's reasoning is a black box.
3. **Integrated trading.** Mantic provides predictions. Cassandra trades on them.
4. **Publication pipeline.** Cassandra is built to produce essays and charts, not just probabilities.

### 14.2 vs. Good Judgment

Good Judgment uses human superforecasters with a proprietary aggregation algorithm. Cassandra:

1. **Operates 24/7** without human forecaster availability constraints
2. **Scales to thousands of questions** simultaneously
3. **Identifies novel questions** rather than only answering pre-defined ones
4. **Trades on its own forecasts** (with human confirmation)

### 14.3 vs. Metaculus Forecasting Tools

The Metaculus `forecasting-tools` repository provides a bot framework for answering Metaculus questions. Cassandra:

1. **Starts upstream** — ingests raw signal, not pre-formed questions
2. **Multi-source ensemble** — not just LLM prompting
3. **Includes base rate engine and time series models** — not just LLM judgment
4. **Full pipeline to trading and publication** — not just prediction

---

## 15. IMPLEMENTATION PHASES

### Phase 1: Foundation (Weeks 1-3)
- Database setup (PostgreSQL + pgvector + DuckDB)
- Ingestion pipeline (YouTube, Substack, RSS, Metaculus API, Kalshi API)
- Embedding pipeline (Ollama nomic-embed-text)
- CLI skeleton (typer + rich)
- Basic forecasting: Claude Opus 4.6 single-agent forecaster on Metaculus questions

### Phase 2: Discovery Engine (Weeks 4-6)
- HDBSCAN topic modeling
- Naive Observer protocol (Van Riper)
- Neustadt-May oscillation protocol
- Five Whys engine
- Cross-domain collision detection
- Question operationalization pipeline

### Phase 3: Forecast Ensemble (Weeks 7-9)
- Multi-component forecasting (Claude deep, Claude adversary, Ollama, market-implied, base rate, time series)
- Aggregation algorithm with extremization
- Calibration tracking and Brier scoring
- Forecast update triggers

### Phase 4: Trading & Publication (Weeks 10-12)
- Kalshi API trading integration
- IBKR TWS API ForecastEx integration
- Edge detection + Kelly criterion sizing
- Risk management rules
- Chart generation (Altair + Plotly)
- Essay generation pipeline
- Substack export

### Phase 5: Learning Loop (Ongoing)
- Automated scoring as questions resolve
- Component weight optimization
- Bias audit system
- Backtesting framework
- Extremization parameter tuning

---

## 16. SUCCESS METRICS

| Metric | Target | Measurement |
|--------|--------|-------------|
| Brier Score (overall) | < 0.18 by month 6, < 0.15 by month 12 | Tracked in `forecast_scores` |
| Brier Score vs. Metaculus Community | Beat community on >50% of overlapping questions | Direct comparison |
| Novel questions generated | >10 high-quality novel questions per month | Manual review |
| Trading P&L | Positive after 6 months | `positions` table |
| Calibration | Within 5% of perfect calibration for all buckets | Calibration chart |
| Essays published | 2-4 per month | Output count |
| System uptime | >95% of scheduled jobs complete on time | Cron monitoring |

---

## 17. OPEN QUESTIONS & RISKS

1. **Claude API rate limits under Max subscription:** Need to confirm how many API calls per day are available. May need to batch requests efficiently.
2. **Ollama 70B model performance on M-series:** Real-world inference speed for llama3.3:70b needs benchmarking. May need to drop to 32B if too slow.
3. **Brave Search free tier (2000 queries/month):** May need to supplement with other free search APIs or use local search over ingested corpus.
4. **Kalshi account verification and funding requirements:** Need active funded account for trading.
5. **IBKR TWS API requires TWS or IB Gateway running:** Need to keep TWS running on Mac Studio.
6. **Legal considerations for automated trading on prediction markets:** Review Kalshi and IBKR terms of service for bot trading.
7. **Reflexivity in trading:** The very act of trading on Cassandra's forecasts may move thin markets and reduce edge.

---

*"The future belongs to adults who can think like four-year-olds." — Dan Gardner*

*Cassandra is the four-year-old with a PostgreSQL database and a trading account.*


Implement the full pipeline.

DO NOT DOWNGRADE/TRADE-OFF. STOP IF YOU NEED MY HELP. BUT WHEN YOU CAN MOVE ONTO OTHER PARTS OF THE SYSTEM AND COMPLETE THOSE AND THEN STOP AND REPORT TO ME WHEN YOU ARE TRULY BLOCKED.

Apply the full pipeline to.

The topic:

- Education
- US education
- Public education
- Texas education
- Waco Texas education
- Waco Texas ISD

Sources:

- Find your own
- Substack (use /feed URL once you discover the publication, e.g. https://dgardner.substack.com/feed )
- YouTube (download transcript once you find the video)
- Project Gutenberg
- The Internet Archive
- US census data
- The Texas Tribune https://www.texastribune.org/

DO NOT DOWNGRADE/TRADE-OFF. STOP IF YOU NEED MY HELP.
