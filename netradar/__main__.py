import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.live import Live

from .config import load_config
from .monitor import EndpointMonitor
from .display import build_table
from .alert import AlertManager


@click.command()
@click.option("--config", "-c", default="config.yaml", show_default=True,
              help="Path to config file.")
@click.option("--interval", "-i", type=float, default=None,
              help="Override measurement interval in seconds.")
@click.option("--no-alerts", is_flag=True, default=False,
              help="Disable macOS system notifications.")
def cli(config: str, interval: float | None, no_alerts: bool) -> None:
    """Network stability monitor — tracks latency, jitter and packet loss."""
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"Config file not found: {config_path}", err=True)
        sys.exit(1)

    cfg = load_config(config_path)
    if interval is not None:
        cfg.interval = interval

    monitors = [EndpointMonitor(ep, cfg) for ep in cfg.endpoints]
    alert_mgr = AlertManager() if not no_alerts else None
    console = Console()

    async def run() -> None:
        with Live(build_table(monitors), console=console, refresh_per_second=4) as live:
            while True:
                await asyncio.gather(*(m.measure() for m in monitors))

                if alert_mgr:
                    for m in monitors:
                        await alert_mgr.check(m)

                live.update(build_table(monitors))
                await asyncio.sleep(cfg.interval)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")


if __name__ == "__main__":
    cli()
