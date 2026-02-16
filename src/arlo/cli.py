"""Arlo CLI entry point using Typer."""
import typer
from dotenv import load_dotenv

app = typer.Typer(
    name="arlo",
    help="Arlo: AI Superforecasting System for prediction markets",
    no_args_is_help=True,
)

# --- Ingest commands ---

@app.command()
def ingest(
    source: str = typer.Option(..., help="Source type: youtube, substack, news, markets, economic, academic"),
    channel: str = typer.Option(None, help="Specific channel/publication (for youtube/substack)"),
    full: bool = typer.Option(False, help="Full refresh (for economic data)"),
):
    """Run ingestion for a specific source."""
    from rich.console import Console
    from arlo.ingest.pipeline import get_pipeline

    console = Console()
    pipeline = get_pipeline()

    if source not in pipeline.registered_types:
        available = ", ".join(pipeline.registered_types)
        console.print(f"[red]Unknown source type: {source}[/red]")
        console.print(f"Available: {available}")
        raise typer.Exit(1)

    console.print(f"[bold]Running ingestion for [cyan]{source}[/cyan]...[/bold]")
    try:
        pipeline.run(source)
        console.print(f"[green]Ingestion complete for {source}.[/green]")
    except Exception as e:
        console.print(f"[red]Ingestion failed: {e}[/red]")
        raise typer.Exit(1)

# --- Discover commands ---
@app.command()
def discover(
    window: str = typer.Option("7d", help="Time window for discovery (e.g., 7d, 30d)"),
):
    """Run domain discovery and gap analysis."""
    from rich.console import Console
    Console().print(f"[yellow]discover --window {window} not yet implemented[/yellow]")

# --- Question commands ---
@app.command()
def question(
    domain: str = typer.Option(None, help="Specific domain to operationalize"),
    from_discovery: bool = typer.Option(False, "--from-discovery", help="Generate from latest discovery output"),
):
    """Generate operationalized forecasting questions."""
    from rich.console import Console
    Console().print("[yellow]question not yet implemented[/yellow]")

# --- Forecast commands ---

@app.command()
def forecast(
    question_id: int = typer.Option(None, help="Forecast specific question"),
    all_active: bool = typer.Option(False, "--all-active", help="Forecast all active questions"),
):
    """Run forecast engine."""
    from rich.console import Console
    Console().print("[yellow]forecast not yet implemented[/yellow]")

# --- Trading commands ---
trade_app = typer.Typer(help="Trading commands")
app.add_typer(trade_app, name="trade")

# Kalshi subcommands
kalshi_app = typer.Typer(help="Kalshi prediction market commands")
trade_app.add_typer(kalshi_app, name="kalshi")

@kalshi_app.command("balance")
def kalshi_balance():
    """Show Kalshi account balance."""
    from arlo.trade.kalshi_client import get_client, get_balance
    from arlo.shared.display import print_balance
    try:
        client = get_client()
        bal = get_balance(client)
        print_balance("Kalshi", bal)
    except KeyError as e:
        from arlo.shared.display import print_error
        print_error(f"Missing env var: {e}. Check your .env file.")
        raise typer.Exit(1)

@kalshi_app.command("positions")
def kalshi_positions():
    """Show Kalshi open positions."""
    from arlo.trade.kalshi_client import get_client, get_positions
    from arlo.shared.display import console, print_table
    try:
        client = get_client()
        pos = get_positions(client)
        if not pos:
            console.print("No open positions.")
            return
        print_table(
            "Kalshi Positions",
            ["Ticker", "Side", "Quantity", "Avg Price"],
            [(p.ticker, p.side, p.quantity, f"{p.average_price}c") for p in pos],
        )
    except KeyError as e:
        from arlo.shared.display import print_error
        print_error(f"Missing env var: {e}. Check your .env file.")
        raise typer.Exit(1)

@kalshi_app.command("markets")
def kalshi_markets(
    status: str = typer.Option("open", help="Market status filter"),
    limit: int = typer.Option(20, help="Number of results"),
    search: str = typer.Option(None, help="Search keyword"),
):
    """List or search Kalshi markets."""
    from arlo.trade.kalshi_client import get_client, get_markets
    from arlo.shared.display import console, print_table
    try:
        client = get_client()
        mkts = get_markets(client, status=status, limit=limit)
        if search:
            mkts = [m for m in mkts if search.lower() in (m.title or "").lower()]
        if not mkts:
            console.print("No markets found.")
            return
        print_table(
            "Markets",
            ["Ticker", "Title", "Status", "Yes Price", "Volume"],
            [(m.ticker, (m.title or "")[:50], m.status, m.yes_price, m.volume) for m in mkts],
        )
    except KeyError as e:
        from arlo.shared.display import print_error
        print_error(f"Missing env var: {e}. Check your .env file.")
        raise typer.Exit(1)

@kalshi_app.command("detail")
def kalshi_detail(ticker: str = typer.Argument(..., help="Market ticker")):
    """Show market details."""
    from arlo.trade.kalshi_client import get_client, get_market
    from arlo.shared.display import console
    try:
        client = get_client()
        m = get_market(client, ticker)
        console.print(f"[bold]{m.title}[/bold]")
        console.print(f"  Ticker:    {m.ticker}")
        console.print(f"  Status:    {m.status}")
        console.print(f"  Yes Price: {m.yes_price}c  |  No Price: {m.no_price}c")
        console.print(f"  Volume:    {m.volume}")
    except KeyError as e:
        from arlo.shared.display import print_error
        print_error(f"Missing env var: {e}. Check your .env file.")
        raise typer.Exit(1)

@kalshi_app.command("orderbook")
def kalshi_orderbook(
    ticker: str = typer.Argument(..., help="Market ticker"),
    depth: int = typer.Option(10, help="Orderbook depth"),
):
    """Show orderbook for a market."""
    from arlo.trade.kalshi_client import get_client, get_orderbook
    from arlo.shared.display import console, print_table
    try:
        client = get_client()
        ob = get_orderbook(client, ticker, depth)
        console.print(f"[bold]Orderbook: {ticker}[/bold]")
        if hasattr(ob, "yes") and ob.yes:
            print_table("Yes (Bids)", ["Price", "Quantity"], ob.yes)
        if hasattr(ob, "no") and ob.no:
            print_table("No (Asks)", ["Price", "Quantity"], ob.no)
    except KeyError as e:
        from arlo.shared.display import print_error
        print_error(f"Missing env var: {e}. Check your .env file.")
        raise typer.Exit(1)

@kalshi_app.command("buy")
def kalshi_buy(
    ticker: str = typer.Argument(..., help="Market ticker"),
    side: str = typer.Option(..., help="Buy yes or no"),
    count: int = typer.Option(..., help="Number of contracts"),
    price: int = typer.Option(..., help="Limit price in cents (1-99)"),
):
    """Buy yes or no contracts on Kalshi."""
    from arlo.trade.kalshi_client import get_client, create_order
    from arlo.shared.display import console, print_error, confirm_order
    side = side.lower()
    if side not in ("yes", "no"):
        print_error("Side must be 'yes' or 'no'.")
        raise typer.Exit(1)
    if not 1 <= price <= 99:
        print_error("Price must be between 1 and 99 cents.")
        return
    details = {
        "Ticker": ticker, "Side": side, "Count": count,
        "Price": f"{price}c (${price / 100:.2f})",
        "Total Cost": f"${count * price / 100:.2f}",
    }
    if not confirm_order(details):
        return
    try:
        client = get_client()
        order = create_order(client, ticker, side, count, price)
        console.print(f"[green]Order placed:[/green] {order.order_id} — {order.status}")
    except KeyError as e:
        print_error(f"Missing env var: {e}. Check your .env file.")
        raise typer.Exit(1)

@kalshi_app.command("orders")
def kalshi_orders():
    """List Kalshi open orders."""
    from arlo.trade.kalshi_client import get_client, get_orders
    from arlo.shared.display import console, print_table
    try:
        client = get_client()
        ords = get_orders(client)
        if not ords:
            console.print("No open orders.")
            return
        print_table(
            "Open Orders",
            ["Order ID", "Ticker", "Side", "Remaining", "Price", "Status"],
            [(o.order_id[:12], o.ticker, o.side, o.remaining_count, o.yes_price or o.no_price, o.status) for o in ords],
        )
    except KeyError as e:
        from arlo.shared.display import print_error
        print_error(f"Missing env var: {e}. Check your .env file.")
        raise typer.Exit(1)

@kalshi_app.command("cancel")
def kalshi_cancel(order_id: str = typer.Argument(..., help="Order ID to cancel")):
    """Cancel a Kalshi order."""
    from arlo.trade.kalshi_client import get_client, cancel_order
    from arlo.shared.display import console
    try:
        client = get_client()
        cancel_order(client, order_id)
        console.print(f"[green]Order {order_id} cancelled.[/green]")
    except KeyError as e:
        from arlo.shared.display import print_error
        print_error(f"Missing env var: {e}. Check your .env file.")
        raise typer.Exit(1)

# ForecastEx subcommands
fx_app = typer.Typer(help="ForecastEx (Interactive Brokers) commands")
trade_app.add_typer(fx_app, name="fx")

@fx_app.command("balance")
def fx_balance():
    """Show ForecastEx account balance."""
    from arlo.trade.ibkr_client import connect, get_balance
    from arlo.shared.display import console, print_error
    try:
        conn = connect()
        results = get_balance(conn)
        for r in results:
            if r["tag"] == "TotalCashValue":
                console.print(f"[bold]ForecastEx (IB)[/bold] balance: ${float(r['value']):,.2f} {r['currency']}")
    except Exception as e:
        print_error(f"Cannot connect to TWS/IB Gateway: {e}")
        raise typer.Exit(1)

@fx_app.command("positions")
def fx_positions():
    """Show ForecastEx positions."""
    from arlo.trade.ibkr_client import connect, get_positions
    from arlo.shared.display import console, print_table, print_error
    try:
        conn = connect()
        pos = get_positions(conn)
        if not pos:
            console.print("No open positions.")
            return
        print_table(
            "ForecastEx Positions",
            ["Symbol", "Expiry", "Strike", "Side", "Qty", "Avg Cost"],
            [(p["symbol"], p["expiry"], p["strike"], "Yes" if p["right"] == "C" else "No", int(p["pos"]), f"${p['avgCost']:.2f}") for p in pos],
        )
    except Exception as e:
        print_error(f"Cannot connect to TWS/IB Gateway: {e}")
        raise typer.Exit(1)

@fx_app.command("buy")
def fx_buy(
    symbol: str = typer.Argument(..., help="Contract symbol"),
    expiry: str = typer.Option(..., help="Expiry date YYYYMMDD"),
    strike: float = typer.Option(..., help="Strike price"),
    right: str = typer.Option(..., help="C=Yes, P=No"),
    count: int = typer.Option(..., help="Number of contracts"),
    price: float = typer.Option(..., help="Limit price (0.01-0.99)"),
    tif: str = typer.Option("GTC", help="Time in force: DAY, GTC, IOC"),
):
    """Buy a ForecastEx contract."""
    from arlo.trade.ibkr_client import connect, make_fx_contract, make_fx_order, place_order
    from arlo.shared.display import console, print_error, confirm_order
    contract = make_fx_contract(symbol, expiry, strike, right)
    order = make_fx_order(count, price, tif)
    side_label = "Yes" if right == "C" else "No"
    details = {
        "Symbol": symbol, "Expiry": expiry, "Strike": strike,
        "Side": side_label, "Qty": count, "Price": f"${price:.2f}",
        "Total Cost": f"${count * price:.2f}", "TIF": tif,
    }
    if not confirm_order(details):
        return
    try:
        conn = connect()
        oid = place_order(conn, contract, order)
        console.print(f"[green]Order submitted:[/green] ID={oid}")
    except Exception as e:
        print_error(f"Cannot connect to TWS/IB Gateway: {e}")
        raise typer.Exit(1)

@fx_app.command("orders")
def fx_orders():
    """List ForecastEx open orders."""
    from arlo.trade.ibkr_client import connect, get_orders
    from arlo.shared.display import console, print_table, print_error
    try:
        conn = connect()
        ords = get_orders(conn)
        if not ords:
            console.print("No open orders.")
            return
        print_table(
            "Open Orders",
            ["Order ID", "Symbol", "Right", "Strike", "Action", "Qty", "Price", "Status"],
            [(o["orderId"], o["symbol"], o["right"], o["strike"], o["action"], o["qty"], f"${o['price']:.2f}", o["status"]) for o in ords],
        )
    except Exception as e:
        print_error(f"Cannot connect to TWS/IB Gateway: {e}")
        raise typer.Exit(1)

@fx_app.command("cancel")
def fx_cancel(order_id: int = typer.Argument(..., help="Order ID to cancel")):
    """Cancel a ForecastEx order."""
    from arlo.trade.ibkr_client import connect, cancel_order
    from arlo.shared.display import console, print_error
    try:
        conn = connect()
        cancel_order(conn, order_id)
        console.print(f"[green]Cancel request sent for order {order_id}.[/green]")
    except Exception as e:
        print_error(f"Cannot connect to TWS/IB Gateway: {e}")
        raise typer.Exit(1)

# --- Edge scanning ---
@app.command("scan-edges")
def scan_edges():
    """Show questions where Arlo disagrees with market."""
    from rich.console import Console
    Console().print("[yellow]scan-edges not yet implemented[/yellow]")

# --- Portfolio ---
@app.command()
def portfolio():
    """Show all positions and P&L."""
    from rich.console import Console
    Console().print("[yellow]portfolio not yet implemented[/yellow]")

# --- Explore ---
@app.command()
def explore():
    """Interactive TUI for browsing domains, questions, forecasts."""
    from rich.console import Console
    Console().print("[yellow]explore not yet implemented[/yellow]")

# --- Ask ---
@app.command()
def ask(query: str = typer.Argument(..., help="Your question")):
    """Ask Arlo a free-form question."""
    from rich.console import Console
    Console().print(f"[yellow]ask not yet implemented[/yellow]")

# --- Why ---
@app.command()
def why(topic: str = typer.Argument(..., help="Topic for Five Whys analysis")):
    """Run Five Whys analysis on a topic."""
    from rich.console import Console
    Console().print(f"[yellow]why not yet implemented[/yellow]")

# --- Essay ---
@app.command()
def essay(
    domain: str = typer.Option(..., help="Domain to write about"),
    output: str = typer.Option("output/essays/essay.md", help="Output file path"),
):
    """Generate a publication-quality essay."""
    from rich.console import Console
    Console().print("[yellow]essay not yet implemented[/yellow]")

# --- Chart ---
@app.command()
def chart(
    question_id: int = typer.Option(..., help="Question ID"),
    type: str = typer.Option("forecast-history", help="Chart type"),
):
    """Generate a chart."""
    from rich.console import Console
    Console().print("[yellow]chart not yet implemented[/yellow]")

# --- Score ---
@app.command()
def score():
    """Show Brier score and calibration metrics."""
    from rich.console import Console
    Console().print("[yellow]score not yet implemented[/yellow]")

# --- Audit ---
@app.command()
def audit():
    """Run bias detection audit on forecast history."""
    from rich.console import Console
    Console().print("[yellow]audit not yet implemented[/yellow]")

# --- Backtest ---
@app.command()
def backtest(
    config: str = typer.Option(None, help="Config file for backtest"),
    questions: str = typer.Option(None, help="Question set (e.g., metaculus-2024)"),
):
    """Run historical backtest."""
    from rich.console import Console
    Console().print("[yellow]backtest not yet implemented[/yellow]")

# --- Status ---
@app.command()
def status():
    """Show system status."""
    from rich.console import Console
    console = Console()
    console.print("[bold]Arlo[/bold] v0.1.0")
    console.print("Status: [yellow]Setting up...[/yellow]")

# --- Sources ---
sources_app = typer.Typer(help="Manage data sources")
app.add_typer(sources_app, name="sources")

@sources_app.command("list")
def sources_list():
    """List configured data sources."""
    from rich.console import Console
    Console().print("[yellow]sources list not yet implemented[/yellow]")

@sources_app.command("add")
def sources_add(
    type: str = typer.Option(..., help="Source type"),
    url: str = typer.Option(..., help="Source URL"),
):
    """Add a new data source."""
    from rich.console import Console
    Console().print("[yellow]sources add not yet implemented[/yellow]")


# Load .env on module import for CLI usage
def _cli():
    load_dotenv()
    app()

if __name__ == "__main__":
    _cli()
