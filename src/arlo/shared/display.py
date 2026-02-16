import typer
from rich.console import Console
from rich.table import Table

console = Console()


def print_table(title, columns, rows):
    """Print a formatted table."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(v) for v in row])
    console.print(table)


def print_balance(exchange, balance_cents):
    """Print balance, converting from cents to dollars."""
    console.print(f"[bold]{exchange}[/bold] balance: ${balance_cents / 100:.2f}")


def print_error(msg):
    console.print(f"[red]Error:[/red] {msg}")


def confirm_order(details):
    """Interactive confirmation before placing a trade."""
    console.print("\n[bold yellow]Order Preview:[/bold yellow]")
    for k, v in details.items():
        console.print(f"  {k}: {v}")
    return typer.confirm("Place this order?", default=False)
