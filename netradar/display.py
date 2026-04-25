from datetime import datetime

from rich import box
from rich.table import Table
from rich.text import Text

from .monitor import EndpointMonitor

_STATUS_STYLE = {
    "OK": "bold green",
    "WARN": "bold yellow",
    "DOWN": "bold red",
    "UNKNOWN": "dim",
}


def _fmt(val: float | None, unit: str = " ms") -> str:
    if val is None:
        return "—"
    return f"{val:.1f}{unit}"


def build_table(monitors: list[EndpointMonitor]) -> Table:
    table = Table(
        box=box.ROUNDED,
        title=f"[bold cyan]netradar[/bold cyan]  [dim]{datetime.now().strftime('%H:%M:%S')}[/dim]",
        expand=True,
        show_footer=False,
    )
    table.add_column("Endpoint", style="cyan", min_width=16)
    table.add_column("Host", style="dim", min_width=14)
    table.add_column("Latency", justify="right", min_width=10)
    table.add_column("Min / Max", justify="right", min_width=16)
    table.add_column("Jitter", justify="right", min_width=10)
    table.add_column("Loss", justify="right", min_width=7)
    table.add_column("History (last 20)", min_width=22)
    table.add_column("Status", justify="center", min_width=9)

    for m in monitors:
        r = m.latest
        status = m.status
        bad_style = _STATUS_STYLE.get(status, "")

        if r is not None:
            avg_str = _fmt(r.rtt_avg)
            minmax_str = f"{_fmt(r.rtt_min)} / {_fmt(r.rtt_max)}"
            loss_str = f"{r.loss_pct:.0f}%"
        else:
            avg_str = minmax_str = loss_str = "—"

        jitter_str = _fmt(m.jitter)
        is_bad = status in ("WARN", "DOWN")

        table.add_row(
            m.endpoint.name,
            m.endpoint.host,
            Text(avg_str, style=bad_style if is_bad else ""),
            minmax_str,
            Text(jitter_str, style=bad_style if is_bad else ""),
            Text(loss_str, style=bad_style if is_bad else ""),
            m.sparkline,
            Text(status, style=bad_style),
        )

    return table
