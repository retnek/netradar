import asyncio
import re
import time
import statistics
from collections import deque
from dataclasses import dataclass, field

from .config import Config, EndpointConfig, Thresholds

_LOSS_RE = re.compile(
    r"(\d+) packets transmitted, (\d+) (?:packets )?received, ([\d.]+)% packet loss"
)
_RTT_RE = re.compile(
    r"round-trip min/avg/max/(?:stddev|mdev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms"
)

_SPARK_CHARS = " ▁▂▃▄▅▆▇█"


@dataclass
class PingResult:
    timestamp: float
    host: str
    packets_sent: int
    packets_received: int
    loss_pct: float
    rtt_min: float | None = None
    rtt_avg: float | None = None
    rtt_max: float | None = None


async def _ping(host: str, count: int) -> PingResult:
    ts = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", str(count), "-q", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=count * 3 + 5)
        output = stdout.decode()

        loss_m = _LOSS_RE.search(output)
        if not loss_m:
            return PingResult(ts, host, count, 0, 100.0)

        sent = int(loss_m.group(1))
        received = int(loss_m.group(2))
        loss_pct = float(loss_m.group(3))

        rtt_min = rtt_avg = rtt_max = None
        rtt_m = _RTT_RE.search(output)
        if rtt_m:
            rtt_min = float(rtt_m.group(1))
            rtt_avg = float(rtt_m.group(2))
            rtt_max = float(rtt_m.group(3))

        return PingResult(ts, host, sent, received, loss_pct, rtt_min, rtt_avg, rtt_max)

    except (asyncio.TimeoutError, Exception):
        return PingResult(ts, host, count, 0, 100.0)


class EndpointMonitor:
    def __init__(self, endpoint: EndpointConfig, config: Config):
        self.endpoint = endpoint
        self.config = config
        self.thresholds: Thresholds = endpoint.thresholds or config.thresholds
        self.history: deque[PingResult] = deque(maxlen=config.jitter_window)

    async def measure(self) -> PingResult:
        result = await _ping(self.endpoint.host, self.config.ping_count)
        self.history.append(result)
        return result

    @property
    def latest(self) -> PingResult | None:
        return self.history[-1] if self.history else None

    @property
    def jitter(self) -> float | None:
        avgs = [r.rtt_avg for r in self.history if r.rtt_avg is not None]
        if len(avgs) < 2:
            return None
        return statistics.stdev(avgs)

    @property
    def status(self) -> str:
        r = self.latest
        if r is None:
            return "UNKNOWN"
        if r.loss_pct >= 100:
            return "DOWN"
        t = self.thresholds
        if (
            (r.rtt_avg is not None and r.rtt_avg > t.latency_ms)
            or (self.jitter is not None and self.jitter > t.jitter_ms)
            or r.loss_pct > t.packet_loss_pct
        ):
            return "WARN"
        return "OK"

    @property
    def sparkline(self) -> str:
        avgs = [r.rtt_avg for r in self.history if r.rtt_avg is not None]
        if not avgs:
            return ""
        min_v, max_v = min(avgs), max(avgs)
        if max_v == min_v:
            return "▄" * len(avgs)
        return "".join(
            _SPARK_CHARS[int((v - min_v) / (max_v - min_v) * 8)]
            for v in avgs
        )
