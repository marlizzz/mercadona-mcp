"""Command-line entry point for MercadonaMCP."""

import typer

app = typer.Typer(
    add_completion=False,
    help="MercadonaMCP local companion.",
    no_args_is_help=True,
)
