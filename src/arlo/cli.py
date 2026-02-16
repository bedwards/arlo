import typer

app = typer.Typer(
    name="arlo",
    help="Arlo: AI Superforecasting System for prediction markets",
)

@app.command()
def status():
    """Show system status."""
    from rich.console import Console
    console = Console()
    console.print("[bold]Arlo[/bold] v0.1.0")
    console.print("Status: [yellow]Setting up...[/yellow]")

if __name__ == "__main__":
    app()
