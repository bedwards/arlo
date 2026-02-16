import click

from pmcli.display import console, print_table, print_error, confirm_order


def _get_ib_conn(ctx):
    """Lazily create and cache the IB connection."""
    if "ib_conn" not in ctx.obj:
        from pmcli.forecastex.client import connect

        try:
            ctx.obj["ib_conn"] = connect()
        except Exception as e:
            print_error(f"Cannot connect to TWS/IB Gateway: {e}")
            print_error("Ensure TWS or IB Gateway is running with API connections enabled.")
            raise SystemExit(1)
    return ctx.obj["ib_conn"]


@click.group(name="fx")
@click.pass_context
def fx(ctx):
    """ForecastEx (Interactive Brokers) commands."""
    pass


@fx.command()
@click.pass_context
def balance(ctx):
    """Show account balance."""
    from pmcli.forecastex.client import get_balance

    results = get_balance(_get_ib_conn(ctx))
    for r in results:
        if r["tag"] == "TotalCashValue":
            console.print(
                f"[bold]ForecastEx (IB)[/bold] balance: ${float(r['value']):,.2f} {r['currency']}"
            )


@fx.command()
@click.pass_context
def positions(ctx):
    """Show ForecastEx positions."""
    from pmcli.forecastex.client import get_positions

    pos = get_positions(_get_ib_conn(ctx))
    if not pos:
        console.print("No open positions.")
        return
    print_table(
        "ForecastEx Positions",
        ["Symbol", "Expiry", "Strike", "Side", "Qty", "Avg Cost"],
        [
            (
                p["symbol"],
                p["expiry"],
                p["strike"],
                "Yes" if p["right"] == "C" else "No",
                int(p["pos"]),
                f"${p['avgCost']:.2f}",
            )
            for p in pos
        ],
    )


@fx.command()
@click.argument("symbol")
@click.option("--expiry", required=True, help="Expiry date YYYYMMDD")
@click.option("--strike", required=True, type=float, help="Strike price")
@click.option("--right", required=True, type=click.Choice(["C", "P"]), help="C=Yes, P=No")
@click.option("--count", required=True, type=int, help="Number of contracts")
@click.option("--price", required=True, type=float, help="Limit price (0.01-0.99)")
@click.option("--tif", default="GTC", type=click.Choice(["DAY", "GTC", "IOC"]), help="Time in force")
@click.pass_context
def buy(ctx, symbol, expiry, strike, right, count, price, tif):
    """Buy a ForecastEx contract.

    ForecastEx contracts cannot be sold. To exit a position,
    buy the opposing contract (C for Yes, P for No).
    """
    from pmcli.forecastex.client import make_fx_contract, make_fx_order, place_order

    contract = make_fx_contract(symbol, expiry, strike, right)
    order = make_fx_order(count, price, tif)

    side_label = "Yes" if right == "C" else "No"
    details = {
        "Symbol": symbol,
        "Expiry": expiry,
        "Strike": strike,
        "Side": side_label,
        "Qty": count,
        "Price": f"${price:.2f}",
        "Total Cost": f"${count * price:.2f}",
        "TIF": tif,
    }
    if not confirm_order(details):
        return

    oid = place_order(_get_ib_conn(ctx), contract, order)
    console.print(f"[green]Order submitted:[/green] ID={oid}")


@fx.command()
@click.pass_context
def orders(ctx):
    """List open orders."""
    from pmcli.forecastex.client import get_orders

    ords = get_orders(_get_ib_conn(ctx))
    if not ords:
        console.print("No open orders.")
        return
    print_table(
        "Open Orders",
        ["Order ID", "Symbol", "Right", "Strike", "Action", "Qty", "Price", "Status"],
        [
            (
                o["orderId"],
                o["symbol"],
                o["right"],
                o["strike"],
                o["action"],
                o["qty"],
                f"${o['price']:.2f}",
                o["status"],
            )
            for o in ords
        ],
    )


@fx.command()
@click.argument("order_id", type=int)
@click.pass_context
def cancel(ctx, order_id):
    """Cancel an order by ID."""
    from pmcli.forecastex.client import cancel_order

    cancel_order(_get_ib_conn(ctx), order_id)
    console.print(f"[green]Cancel request sent for order {order_id}.[/green]")
