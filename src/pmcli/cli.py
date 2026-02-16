import click


@click.group()
@click.option("--env-file", default=".env", help="Path to .env file")
@click.pass_context
def cli(ctx, env_file):
    """Prediction markets CLI for Kalshi and ForecastEx."""
    from dotenv import load_dotenv

    load_dotenv(env_file)
    ctx.ensure_object(dict)


# Import and register subcommands
from pmcli.kalshi.commands import kalshi  # noqa: E402
from pmcli.forecastex.commands import fx  # noqa: E402

cli.add_command(kalshi)
cli.add_command(fx)
