import click

from pmcli.display import console, print_table, print_balance, print_error, confirm_order


def _get_kalshi_client(ctx):
    """Lazily create and cache the Kalshi client."""
    if "kalshi_client" not in ctx.obj:
        from pmcli.kalshi.client import get_client

        try:
            ctx.obj["kalshi_client"] = get_client()
        except KeyError as e:
            print_error(f"Missing env var: {e}. Check your .env file.")
            raise SystemExit(1)
    return ctx.obj["kalshi_client"]


@click.group()
@click.pass_context
def kalshi(ctx):
    """Kalshi prediction market commands."""
    pass


@kalshi.command()
@click.pass_context
def balance(ctx):
    """Show account balance."""
    from pmcli.kalshi.client import get_balance

    bal = get_balance(_get_kalshi_client(ctx))
    print_balance("Kalshi", bal)


@kalshi.command()
@click.pass_context
def positions(ctx):
    """Show open positions."""
    from pmcli.kalshi.client import get_positions

    pos = get_positions(_get_kalshi_client(ctx))
    if not pos:
        console.print("No open positions.")
        return
    print_table(
        "Kalshi Positions",
        ["Ticker", "Side", "Quantity", "Avg Price"],
        [(p.ticker, p.side, p.quantity, f"{p.average_price}c") for p in pos],
    )


@kalshi.group()
def markets():
    """Market data commands."""
    pass


@markets.command(name="list")
@click.option("--status", default="open", help="Market status filter")
@click.option("--limit", default=20, type=int, help="Number of results")
@click.pass_context
def list_markets(ctx, status, limit):
    """List markets."""
    from pmcli.kalshi.client import get_markets

    mkts = get_markets(_get_kalshi_client(ctx), status=status, limit=limit)
    if not mkts:
        console.print("No markets found.")
        return
    print_table(
        "Markets",
        ["Ticker", "Title", "Status", "Yes Price", "Volume"],
        [(m.ticker, (m.title or "")[:50], m.status, m.yes_price, m.volume) for m in mkts],
    )


@markets.command()
@click.argument("query")
@click.option("--limit", default=100, type=int, help="Markets to scan")
@click.pass_context
def search(ctx, query, limit):
    """Search markets by keyword."""
    from pmcli.kalshi.client import get_markets

    mkts = get_markets(_get_kalshi_client(ctx), limit=limit)
    filtered = [m for m in mkts if query.lower() in (m.title or "").lower()]
    if not filtered:
        console.print(f"No markets matching '{query}'.")
        return
    print_table(
        f"Markets matching '{query}'",
        ["Ticker", "Title", "Yes Price"],
        [(m.ticker, (m.title or "")[:60], m.yes_price) for m in filtered],
    )


@markets.command()
@click.argument("ticker")
@click.pass_context
def detail(ctx, ticker):
    """Show market details."""
    from pmcli.kalshi.client import get_market

    m = get_market(_get_kalshi_client(ctx), ticker)
    console.print(f"[bold]{m.title}[/bold]")
    console.print(f"  Ticker:    {m.ticker}")
    console.print(f"  Status:    {m.status}")
    console.print(f"  Yes Price: {m.yes_price}c  |  No Price: {m.no_price}c")
    console.print(f"  Volume:    {m.volume}")


@markets.command()
@click.argument("ticker")
@click.option("--depth", default=10, type=int, help="Orderbook depth")
@click.pass_context
def orderbook(ctx, ticker, depth):
    """Show orderbook for a market."""
    from pmcli.kalshi.client import get_orderbook

    ob = get_orderbook(_get_kalshi_client(ctx), ticker, depth)
    console.print(f"[bold]Orderbook: {ticker}[/bold]")
    if hasattr(ob, "yes") and ob.yes:
        print_table("Yes (Bids)", ["Price", "Quantity"], ob.yes)
    if hasattr(ob, "no") and ob.no:
        print_table("No (Asks)", ["Price", "Quantity"], ob.no)


@kalshi.command()
@click.argument("ticker")
@click.option("--side", required=True, type=click.Choice(["yes", "no"]), help="Buy yes or no")
@click.option("--count", required=True, type=int, help="Number of contracts")
@click.option("--price", required=True, type=int, help="Limit price in cents (1-99)")
@click.pass_context
def buy(ctx, ticker, side, count, price):
    """Buy yes or no contracts."""
    from pmcli.kalshi.client import create_order

    if not 1 <= price <= 99:
        print_error("Price must be between 1 and 99 cents.")
        return
    details = {
        "Ticker": ticker,
        "Side": side,
        "Count": count,
        "Price": f"{price}c (${price / 100:.2f})",
        "Total Cost": f"${count * price / 100:.2f}",
    }
    if not confirm_order(details):
        return
    order = create_order(_get_kalshi_client(ctx), ticker, side, count, price)
    console.print(f"[green]Order placed:[/green] {order.order_id} — {order.status}")


@kalshi.command()
@click.pass_context
def orders(ctx):
    """List open orders."""
    from pmcli.kalshi.client import get_orders

    ords = get_orders(_get_kalshi_client(ctx))
    if not ords:
        console.print("No open orders.")
        return
    print_table(
        "Open Orders",
        ["Order ID", "Ticker", "Side", "Remaining", "Price", "Status"],
        [
            (o.order_id[:12], o.ticker, o.side, o.remaining_count, o.yes_price or o.no_price, o.status)
            for o in ords
        ],
    )


@kalshi.command()
@click.argument("order_id")
@click.pass_context
def cancel(ctx, order_id):
    """Cancel an order by ID."""
    from pmcli.kalshi.client import cancel_order

    cancel_order(_get_kalshi_client(ctx), order_id)
    console.print(f"[green]Order {order_id} cancelled.[/green]")
