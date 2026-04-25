import asyncio
import time

from .monitor import EndpointMonitor


class AlertManager:
    def __init__(self, cooldown: float = 60.0):
        self.cooldown = cooldown
        self._last_alert: dict[str, float] = {}

    async def check(self, monitor: EndpointMonitor) -> None:
        status = monitor.status
        if status not in ("WARN", "DOWN"):
            return

        host = monitor.endpoint.host
        now = time.time()
        if now - self._last_alert.get(host, 0) < self.cooldown:
            return

        self._last_alert[host] = now
        await self._notify(monitor, status)

    async def _notify(self, monitor: EndpointMonitor, status: str) -> None:
        name = monitor.endpoint.name
        host = monitor.endpoint.host
        r = monitor.latest
        if r is None:
            return

        if status == "DOWN":
            body = f"{name} ({host}) — 100% packet loss"
        else:
            t = monitor.thresholds
            parts = []
            if r.rtt_avg is not None and r.rtt_avg > t.latency_ms:
                parts.append(f"latency {r.rtt_avg:.1f}ms > {t.latency_ms:.0f}ms")
            if monitor.jitter is not None and monitor.jitter > t.jitter_ms:
                parts.append(f"jitter {monitor.jitter:.1f}ms > {t.jitter_ms:.0f}ms")
            if r.loss_pct > t.packet_loss_pct:
                parts.append(f"loss {r.loss_pct:.0f}% > {t.packet_loss_pct:.0f}%")
            body = f"{name} ({host}): {', '.join(parts)}"

        title = f"netradar — {status}"
        script = f'display notification "{body}" with title "{title}" sound name "Ping"'
        await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
