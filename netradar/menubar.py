import rumps

from .config import Config, Thresholds
from .storage import Storage

_ICON = {"OK": "●", "WARN": "⚠", "DOWN": "✕", "UNKNOWN": "○"}
_TITLE = {"OK": "●", "WARN": "⚠", "DOWN": "✕", "UNKNOWN": "◉"}


def _status(row: dict, thresholds: Thresholds) -> str:
    if row["loss_pct"] >= 100:
        return "DOWN"
    rtt = row.get("rtt_avg")
    jitter = row.get("jitter")
    loss = row.get("loss_pct", 0)
    if (
        (rtt is not None and rtt > thresholds.latency_ms)
        or (jitter is not None and jitter > thresholds.jitter_ms)
        or loss > thresholds.packet_loss_pct
    ):
        return "WARN"
    return "OK"


def _fmt(val: float | None, unit: str = "ms") -> str:
    return f"{val:.1f}{unit}" if val is not None else "—"


class NetradarMenuBar(rumps.App):
    POLL = 10

    def __init__(self, config: Config, storage: Storage):
        super().__init__("netradar", title="◉")
        self.config = config
        self.storage = storage

        self._thresh: dict[str, Thresholds] = {
            ep.name: ep.thresholds or config.thresholds
            for ep in config.endpoints
        }

        # Header (non-clickable display item)
        hdr = rumps.MenuItem("  Endpoint               Latency   ±Jitter    Loss")
        hdr.set_callback(None)
        self.menu.add(hdr)
        sep = rumps.MenuItem("  " + "─" * 50)
        sep.set_callback(None)
        self.menu.add(sep)

        # One item per endpoint — titles updated on each poll
        self._ep_items: dict[str, rumps.MenuItem] = {}
        for ep in config.endpoints:
            item = rumps.MenuItem(f"  ○ {ep.name:<23} —")
            item.set_callback(None)
            self._ep_items[ep.name] = item
            self.menu.add(item)

        rumps.Timer(self._refresh, self.POLL).start()
        self._refresh(None)

    def _refresh(self, _) -> None:
        rows = {r["endpoint"]: r for r in self.storage.latest_per_endpoint()}
        statuses: list[str] = []

        for ep in self.config.endpoints:
            item = self._ep_items.get(ep.name)
            if item is None:
                continue
            row = rows.get(ep.name)
            if row is None:
                item.title = f"  ○ {ep.name:<23} waiting..."
                statuses.append("UNKNOWN")
                continue

            status = _status(row, self._thresh[ep.name])
            statuses.append(status)

            rtt = _fmt(row.get("rtt_avg"))
            jitter = _fmt(row.get("jitter"))
            loss = f"{row['loss_pct']:.0f}%"
            icon = _ICON[status]

            item.title = (
                f"  {icon} {ep.name:<23}"
                f" {rtt:>8}  {jitter:>8}  {loss:>5}"
            )

        worst = (
            "DOWN" if "DOWN" in statuses
            else "WARN" if "WARN" in statuses
            else "OK" if "OK" in statuses
            else "UNKNOWN"
        )
        self.title = _TITLE[worst]


def run(config: Config, storage: Storage) -> None:
    NetradarMenuBar(config, storage).run()
