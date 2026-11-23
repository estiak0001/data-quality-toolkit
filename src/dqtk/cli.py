import logging
import sys

import click

from dqtk.checks.base import Status
from dqtk.config import load_config
from dqtk.runner import run_all


@click.group()
def main() -> None:
    """dqtk — a pluggable data quality and observability toolkit."""


@main.command()
@click.option(
    "--config", "config_path", required=True, type=click.Path(exists=True), help="Path to config.yml"
)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def run(config_path: str, verbose: bool) -> None:
    """Run every configured check against every configured table."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    config = load_config(config_path)
    try:
        outcomes = run_all(config)
    finally:
        config.close()

    exit_code = 0
    for table, results in outcomes.items():
        for result in results:
            if result.status in (Status.FAIL, Status.ERROR):
                exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
