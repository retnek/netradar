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
from .storage import Storage


_CONFIG_OPTION = click.option(
    "--config", "-c", default="config.yaml", show_default=True,
    help="Path to config file.",
)


def _load(config: str):
    path = Path(config)
    if not path.exists():
        click.echo(f"Config file not found: {path}", err=True)
        sys.exit(1)
    return load_config(path), path.resolve()


@click.group()
def cli() -> None:
    """netradar — network stability monitor."""


@cli.command()
@_CONFIG_OPTION
@click.option("--interval", "-i", type=float, default=None,
              help="Override measurement interval in seconds.")
@click.option("--no-alerts", is_flag=True, default=False,
              help="Disable macOS system notifications.")
def monitor(config: str, interval: float | None, no_alerts: bool) -> None:
    """Live TUI: latency, jitter, packet loss per endpoint."""
    cfg, _ = _load(config)
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


@cli.command()
@_CONFIG_OPTION
def daemon(config: str) -> None:
    """Headless daemon: measures and stores to SQLite."""
    cfg, _ = _load(config)
    storage = Storage(cfg.storage)

    from . import daemon as _daemon
    try:
        asyncio.run(_daemon.run(cfg, storage))
    except KeyboardInterrupt:
        pass


@cli.command()
@_CONFIG_OPTION
def menubar(config: str) -> None:
    """macOS menu bar app (reads from SQLite, run daemon separately)."""
    cfg, _ = _load(config)
    storage = Storage(cfg.storage)

    from . import menubar as _menubar
    _menubar.run(cfg, storage)


@cli.command()
@_CONFIG_OPTION
def install(config: str) -> None:
    """Install netradar daemon as a launchd LaunchAgent."""
    import subprocess
    cfg, config_abs = _load(config)

    python = sys.executable
    agents_dir = Path.home() / "Library" / "LaunchAgents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(cfg.storage.path).expanduser().parent / "daemon.log"
    plist_path = agents_dir / "com.netradar.daemon.plist"

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.netradar.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>netradar</string>
        <string>daemon</string>
        <string>--config</string>
        <string>{config_abs}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{config_abs.parent}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""
    plist_path.write_text(plist)
    subprocess.run(["launchctl", "load", str(plist_path)], check=True)
    click.echo(f"Daemon installed and started.")
    click.echo(f"  plist:  {plist_path}")
    click.echo(f"  db:     {Path(cfg.storage.path).expanduser()}")
    click.echo(f"  log:    {log_path}")


@cli.command()
def uninstall() -> None:
    """Stop and remove the launchd LaunchAgent."""
    import subprocess
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.netradar.daemon.plist"
    if not plist_path.exists():
        click.echo("No launchd plist found — nothing to do.")
        return
    subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
    plist_path.unlink()
    click.echo("Daemon stopped and uninstalled.")


if __name__ == "__main__":
    cli()
