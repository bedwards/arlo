"""Government/institutional data ingestion for education metrics.

Fetches time-series data from five public sources:
  - FRED (Federal Reserve Economic Data)
  - Census Bureau (ACS 5-year estimates)
  - BLS (Bureau of Labor Statistics)
  - NCES (National Center for Education Statistics)
  - TEA (Texas Education Agency)

All data is stored in both PostgreSQL (economic_series table) and DuckDB
(economic_series table) for relational and analytical access respectively.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import TYPE_CHECKING

import httpx
import polars as pl
import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# FRED series IDs relevant to education / Waco TX economics
# ---------------------------------------------------------------------------
FRED_SERIES = [
    "MEPAINUSA672N",  # Median personal income
    "UNRATE",         # Unemployment rate
    "CPIAUCSL",       # Consumer Price Index
    "MEHOINUSA672N",  # Median household income
    "SLOAS",          # Student loans outstanding (total)
]

# BLS education-sector employment series
BLS_SERIES = [
    "CEU6561000001",  # Educational services, all employees
]

# Census ACS variables for McLennan County TX (FIPS 48-309)
CENSUS_STATE_FIPS = "48"
CENSUS_COUNTY_FIPS = "309"
CENSUS_VARIABLES = [
    "B15003_001E",  # Educational attainment - total population 25+
    "B15003_017E",  # High school diploma
    "B15003_021E",  # Bachelor's degree
    "B15003_022E",  # Master's degree
    "B15003_023E",  # Professional school degree
    "B15003_024E",  # Doctorate degree
    "B15003_025E",  # (last category)
    "B14001_001E",  # School enrollment - total
    "B14001_002E",  # Enrolled in school
]

# Waco ISD district ID for TEA
WACO_ISD_DISTRICT_ID = "161914"

# Default HTTP timeout (seconds)
HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# FRED
# ---------------------------------------------------------------------------


def fetch_fred_series(
    series_ids: list[str] | None = None,
    api_key: str | None = None,
    full: bool = False,
) -> pl.DataFrame:
    """Fetch observation data from FRED for the given series IDs.

    Args:
        series_ids: FRED series identifiers. Defaults to ``FRED_SERIES``.
        api_key: FRED API key. Falls back to ``FRED_API_KEY`` env var.
        full: If True, fetch all historical data. Otherwise last 5 years.

    Returns:
        A polars DataFrame with columns: series_id, source, date, value.
    """
    series_ids = series_ids or FRED_SERIES
    api_key = api_key or os.environ.get("FRED_API_KEY", "")
    if not api_key:
        log.warning("fred.no_api_key", hint="Set FRED_API_KEY env var for FRED access")
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    base_url = "https://api.stlouisfed.org/fred/series/observations"
    frames: list[pl.DataFrame] = []

    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        for sid in series_ids:
            params: dict = {
                "series_id": sid,
                "api_key": api_key,
                "file_type": "json",
            }
            if not full:
                # Last 5 years
                params["observation_start"] = str(date(date.today().year - 5, 1, 1))

            log.info("fred.fetch", series_id=sid, full=full)
            try:
                resp = client.get(base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                log.error("fred.http_error", series_id=sid, error=str(exc))
                continue

            observations = data.get("observations", [])
            if not observations:
                log.warning("fred.no_data", series_id=sid)
                continue

            rows = []
            for obs in observations:
                val_str = obs.get("value", ".")
                if val_str == ".":
                    continue  # FRED uses "." for missing values
                try:
                    rows.append({
                        "series_id": sid,
                        "source": "FRED",
                        "date": obs["date"],
                        "value": float(val_str),
                    })
                except (ValueError, KeyError):
                    continue

            if rows:
                df = pl.DataFrame(rows).with_columns(
                    pl.col("date").str.to_date("%Y-%m-%d")
                )
                frames.append(df)
                log.info("fred.fetched", series_id=sid, rows=len(rows))

    if not frames:
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})
    return pl.concat(frames)


# ---------------------------------------------------------------------------
# Census Bureau
# ---------------------------------------------------------------------------


def fetch_census_education(year: int = 2023) -> pl.DataFrame:
    """Fetch ACS 5-year education attainment data for McLennan County TX.

    Args:
        year: ACS year to query (uses 5-year estimates).

    Returns:
        A polars DataFrame with columns: series_id, source, date, value.
    """
    variables = ",".join(CENSUS_VARIABLES)
    url = (
        f"https://api.census.gov/data/{year}/acs/acs5"
        f"?get=NAME,{variables}"
        f"&for=county:{CENSUS_COUNTY_FIPS}"
        f"&in=state:{CENSUS_STATE_FIPS}"
    )

    api_key = os.environ.get("CENSUS_API_KEY", "")
    if api_key:
        url += f"&key={api_key}"

    log.info("census.fetch", year=year, county="McLennan County TX")
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        log.error("census.http_error", error=str(exc))
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    if len(data) < 2:
        log.warning("census.no_data", year=year)
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    headers = data[0]
    values = data[1]

    # Census returns [NAME, var1, var2, ..., state, county]
    # Map variable columns to values
    ref_date = date(year, 1, 1)
    rows = []
    for header, val in zip(headers, values):
        if header in ("NAME", "state", "county"):
            continue
        try:
            rows.append({
                "series_id": f"CENSUS_ACS5_{header}",
                "source": "Census",
                "date": ref_date,
                "value": float(val) if val is not None else None,
            })
        except (ValueError, TypeError):
            continue

    # Filter out None values
    rows = [r for r in rows if r["value"] is not None]

    if not rows:
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    df = pl.DataFrame(rows)
    log.info("census.fetched", year=year, rows=len(rows))
    return df


# ---------------------------------------------------------------------------
# BLS
# ---------------------------------------------------------------------------


def fetch_bls_series(
    series_ids: list[str] | None = None,
    full: bool = False,
) -> pl.DataFrame:
    """Fetch time-series data from the Bureau of Labor Statistics.

    Args:
        series_ids: BLS series identifiers. Defaults to ``BLS_SERIES``.
        full: If True, fetch 20 years of data. Otherwise last 5 years.

    Returns:
        A polars DataFrame with columns: series_id, source, date, value.
    """
    series_ids = series_ids or BLS_SERIES
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    current_year = date.today().year
    start_year = current_year - 20 if full else current_year - 5
    end_year = current_year

    payload: dict = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }

    # Optional BLS API key for higher rate limits
    bls_key = os.environ.get("BLS_API_KEY", "")
    if bls_key:
        payload["registrationkey"] = bls_key

    log.info("bls.fetch", series_ids=series_ids, start_year=start_year, end_year=end_year)
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        log.error("bls.http_error", error=str(exc))
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    if data.get("status") != "REQUEST_SUCCEEDED":
        log.error("bls.api_error", message=data.get("message", []))
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    rows = []
    for series in data.get("Results", {}).get("series", []):
        sid = series.get("seriesID", "")
        for item in series.get("data", []):
            year = int(item["year"])
            period = item["period"]  # e.g., "M01" for January
            if not period.startswith("M"):
                continue  # Skip annual/quarterly aggregates
            month = int(period[1:])
            try:
                rows.append({
                    "series_id": sid,
                    "source": "BLS",
                    "date": date(year, month, 1),
                    "value": float(item["value"]),
                })
            except (ValueError, KeyError):
                continue

    if not rows:
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    df = pl.DataFrame(rows)
    log.info("bls.fetched", rows=len(rows))
    return df


# ---------------------------------------------------------------------------
# NCES (National Center for Education Statistics)
# ---------------------------------------------------------------------------


def fetch_nces_district(district_name: str = "Waco") -> pl.DataFrame:
    """Fetch school district data from the NCES Common Core of Data API.

    Uses the NCES Edge geocoding/search API to find district info.

    Args:
        district_name: Name of the school district to look up.

    Returns:
        A polars DataFrame with columns: series_id, source, date, value.
    """
    # NCES CCD API endpoint for district search
    url = "https://nces.ed.gov/ccd/schoolsearch/school_list.asp"
    # Use the NCES API (Education Data Portal from Urban Institute as a proxy)
    api_url = (
        "https://educationdata.urban.org/api/v1/schools/ccd/directory/"
        f"?district_name={district_name}&state_fips=48&year=2022"
    )

    log.info("nces.fetch", district_name=district_name)
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.get(api_url)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        log.error("nces.http_error", error=str(exc))
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    results = data.get("results", [])
    if not results:
        log.warning("nces.no_data", district_name=district_name)
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    # Aggregate school-level data into district-level metrics
    ref_date = date(2022, 1, 1)
    enrollment_total = 0
    school_count = 0
    free_lunch_total = 0

    for school in results:
        school_count += 1
        enrollment = school.get("enrollment", 0)
        if enrollment and enrollment > 0:
            enrollment_total += enrollment
        free_lunch = school.get("free_lunch", 0)
        if free_lunch and free_lunch > 0:
            free_lunch_total += free_lunch

    rows = [
        {"series_id": f"NCES_{district_name.upper()}_ENROLLMENT", "source": "NCES", "date": ref_date, "value": float(enrollment_total)},
        {"series_id": f"NCES_{district_name.upper()}_SCHOOL_COUNT", "source": "NCES", "date": ref_date, "value": float(school_count)},
        {"series_id": f"NCES_{district_name.upper()}_FREE_LUNCH", "source": "NCES", "date": ref_date, "value": float(free_lunch_total)},
    ]

    df = pl.DataFrame(rows)
    log.info("nces.fetched", district=district_name, schools=school_count, enrollment=enrollment_total)
    return df


# ---------------------------------------------------------------------------
# TEA (Texas Education Agency)
# ---------------------------------------------------------------------------


def fetch_tea_district(district_id: str | None = None) -> pl.DataFrame:
    """Fetch Texas Academic Performance Report data for a district.

    Uses the TEA public data download / TAPR API.

    Args:
        district_id: TEA district ID. Defaults to Waco ISD (161914).

    Returns:
        A polars DataFrame with columns: series_id, source, date, value.
    """
    district_id = district_id or WACO_ISD_DISTRICT_ID

    # TEA TAPR data is available via their data download portal.
    # We use the Texas Open Data portal API (CKAN-based).
    # Dataset: accountability ratings and performance data.
    url = (
        "https://rptsvr1.tea.texas.gov/cgi/sas/broker"
        "?_service=mariner"
        "&_program=perfrept.perfmast.sas"
        f"&_debug=0&prgopt=reports%2Ftapr%2Fperformance.sas"
        f"&year4=2023&year2=23&topic=perf&gifession=1"
        f"&id={district_id}&ptype=D"
    )

    log.info("tea.fetch", district_id=district_id)

    # TEA data is often served as HTML reports. For structured data,
    # fall back to the Texas Open Data API with known datasets.
    api_url = (
        "https://schoolsdata2-tea-texas.opendata.arcgis.com/api/v2/datasets"
    )

    # Attempt to get data from the TEA ArcGIS Open Data Hub
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            # Try the district performance snapshot
            snapshot_url = (
                "https://services.arcgis.com/0L95CJ0VTaxqcked/arcgis/rest/services/"
                "TAPR_2023/FeatureServer/0/query"
                f"?where=DISTRICT%3D%27{district_id}%27"
                "&outFields=*&f=json"
            )
            resp = client.get(snapshot_url)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        log.error("tea.http_error", error=str(exc))
        return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})

    features = data.get("features", [])
    if not features:
        # Fall back to basic TEA known data points for Waco ISD
        log.warning("tea.no_api_data", district_id=district_id, hint="Using fallback known values")
        return _tea_fallback(district_id)

    ref_date = date(2023, 1, 1)
    rows = []
    for feature in features:
        attrs = feature.get("attributes", {})
        for key, val in attrs.items():
            if val is None:
                continue
            try:
                float_val = float(val)
            except (ValueError, TypeError):
                continue
            rows.append({
                "series_id": f"TEA_{district_id}_{key}",
                "source": "TEA",
                "date": ref_date,
                "value": float_val,
            })

    if not rows:
        return _tea_fallback(district_id)

    df = pl.DataFrame(rows)
    log.info("tea.fetched", district_id=district_id, metrics=len(rows))
    return df


def _tea_fallback(district_id: str) -> pl.DataFrame:
    """Return an empty DataFrame when TEA API is not reachable.

    This placeholder ensures the pipeline continues gracefully even when
    the TEA ArcGIS endpoint is unavailable or restructured.
    """
    log.info("tea.fallback", district_id=district_id)
    return pl.DataFrame(schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64})


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def store_series(df: pl.DataFrame, session: Session) -> int:
    """Upsert economic series data into the PostgreSQL economic_series table.

    Uses PostgreSQL ON CONFLICT DO UPDATE for upsert semantics on the
    composite primary key (series_id, source, date).

    Args:
        df: A polars DataFrame with columns series_id, source, date, value.
        session: SQLAlchemy session.

    Returns:
        Number of rows upserted.
    """
    if df.is_empty():
        return 0

    from arlo.db.models import EconomicSeries

    records = df.to_dicts()

    # Convert polars date objects to Python date objects for SQLAlchemy
    for rec in records:
        if isinstance(rec["date"], str):
            rec["date"] = datetime.strptime(rec["date"], "%Y-%m-%d").date()

    stmt = pg_insert(EconomicSeries.__table__).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["series_id", "source", "date"],
        set_={"value": stmt.excluded.value},
    )

    session.execute(stmt)
    session.commit()
    log.info("postgres.upserted", rows=len(records))
    return len(records)


def store_to_duckdb(df: pl.DataFrame) -> int:
    """Append or upsert economic series data into DuckDB analytical store.

    Creates the economic_series table if it does not exist, then performs
    an INSERT OR REPLACE for upsert semantics.

    Args:
        df: A polars DataFrame with columns series_id, source, date, value.

    Returns:
        Number of rows stored.
    """
    if df.is_empty():
        return 0

    from arlo.db.duckdb_conn import get_duckdb_connection

    conn = get_duckdb_connection()

    # Create table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS economic_series (
            series_id VARCHAR,
            source VARCHAR,
            date DATE,
            value DOUBLE,
            PRIMARY KEY (series_id, source, date)
        )
    """)

    # Register the polars DataFrame and do INSERT OR REPLACE
    conn.register("_staging", df.to_arrow())
    conn.execute("""
        INSERT OR REPLACE INTO economic_series
        SELECT series_id, source, date, value FROM _staging
    """)
    conn.unregister("_staging")

    row_count = df.height
    log.info("duckdb.stored", rows=row_count)
    conn.close()
    return row_count


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def ingest_economic(full: bool = False) -> dict[str, int]:
    """Run the full economic data ingestion pipeline.

    Fetches data from all five sources, transforms with polars, and stores
    in both PostgreSQL and DuckDB. Continues past individual source failures.

    Args:
        full: If True, fetch complete historical data. Otherwise recent only.

    Returns:
        Dict mapping source name to number of rows ingested.
    """
    from rich.console import Console

    console = Console()
    results: dict[str, int] = {}
    all_frames: list[pl.DataFrame] = []

    # --- FRED ---
    console.print("[bold]Fetching FRED economic indicators...[/bold]")
    try:
        fred_df = fetch_fred_series(full=full)
        results["FRED"] = fred_df.height
        if not fred_df.is_empty():
            all_frames.append(fred_df)
        console.print(f"  FRED: {fred_df.height} observations")
    except Exception as exc:
        log.error("ingest.fred_failed", error=str(exc))
        console.print(f"  [red]FRED failed: {exc}[/red]")
        results["FRED"] = 0

    # --- Census ---
    console.print("[bold]Fetching Census Bureau ACS education data...[/bold]")
    try:
        census_years = range(2019, 2024) if full else [2023]
        census_frames = []
        for year in census_years:
            cdf = fetch_census_education(year=year)
            if not cdf.is_empty():
                census_frames.append(cdf)
        census_df = pl.concat(census_frames) if census_frames else pl.DataFrame(
            schema={"series_id": pl.Utf8, "source": pl.Utf8, "date": pl.Date, "value": pl.Float64}
        )
        results["Census"] = census_df.height
        if not census_df.is_empty():
            all_frames.append(census_df)
        console.print(f"  Census: {census_df.height} data points")
    except Exception as exc:
        log.error("ingest.census_failed", error=str(exc))
        console.print(f"  [red]Census failed: {exc}[/red]")
        results["Census"] = 0

    # --- BLS ---
    console.print("[bold]Fetching BLS education employment data...[/bold]")
    try:
        bls_df = fetch_bls_series(full=full)
        results["BLS"] = bls_df.height
        if not bls_df.is_empty():
            all_frames.append(bls_df)
        console.print(f"  BLS: {bls_df.height} observations")
    except Exception as exc:
        log.error("ingest.bls_failed", error=str(exc))
        console.print(f"  [red]BLS failed: {exc}[/red]")
        results["BLS"] = 0

    # --- NCES ---
    console.print("[bold]Fetching NCES school district data...[/bold]")
    try:
        nces_df = fetch_nces_district(district_name="Waco")
        results["NCES"] = nces_df.height
        if not nces_df.is_empty():
            all_frames.append(nces_df)
        console.print(f"  NCES: {nces_df.height} data points")
    except Exception as exc:
        log.error("ingest.nces_failed", error=str(exc))
        console.print(f"  [red]NCES failed: {exc}[/red]")
        results["NCES"] = 0

    # --- TEA ---
    console.print("[bold]Fetching TEA district performance data...[/bold]")
    try:
        tea_df = fetch_tea_district()
        results["TEA"] = tea_df.height
        if not tea_df.is_empty():
            all_frames.append(tea_df)
        console.print(f"  TEA: {tea_df.height} metrics")
    except Exception as exc:
        log.error("ingest.tea_failed", error=str(exc))
        console.print(f"  [red]TEA failed: {exc}[/red]")
        results["TEA"] = 0

    # --- Store combined data ---
    if all_frames:
        combined = pl.concat(all_frames)
        console.print(f"\n[bold]Storing {combined.height} total rows...[/bold]")

        # PostgreSQL
        try:
            from arlo.db.postgres import get_session
            session = get_session()
            pg_count = store_series(combined, session)
            console.print(f"  PostgreSQL: {pg_count} rows upserted")
            session.close()
        except Exception as exc:
            log.error("ingest.postgres_failed", error=str(exc))
            console.print(f"  [red]PostgreSQL storage failed: {exc}[/red]")

        # DuckDB
        try:
            duck_count = store_to_duckdb(combined)
            console.print(f"  DuckDB: {duck_count} rows stored")
        except Exception as exc:
            log.error("ingest.duckdb_failed", error=str(exc))
            console.print(f"  [red]DuckDB storage failed: {exc}[/red]")
    else:
        console.print("\n[yellow]No data fetched from any source.[/yellow]")

    total = sum(results.values())
    console.print(f"\n[bold green]Economic ingestion complete: {total} total rows[/bold green]")
    return results
