import asyncio
import signal

from .alert import AlertManager
from .config import Config
from .monitor import EndpointMonitor
from .storage import Storage


async def run(config: Config, storage: Storage) -> None:
    monitors = [EndpointMonitor(ep, config) for ep in config.endpoints]
    alert_mgr = AlertManager()
    purge_tick = 0

    loop = asyncio.get_running_loop()
    stop: asyncio.Future = loop.create_future()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: stop.set_result(None) if not stop.done() else None)

    async def measure_loop() -> None:
        nonlocal purge_tick
        while not stop.done():
            await asyncio.gather(*(m.measure() for m in monitors))

            for m in monitors:
                r = m.latest
                if r:
                    storage.insert(
                        m.endpoint.name, m.endpoint.host,
                        r.rtt_avg, r.rtt_min, r.rtt_max,
                        r.loss_pct, m.jitter, r.timestamp,
                    )
                await alert_mgr.check(m)

            purge_tick += 1
            if purge_tick >= 720:
                storage.purge_old()
                purge_tick = 0

            try:
                await asyncio.wait_for(asyncio.shield(stop), timeout=config.interval)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

    await asyncio.gather(measure_loop(), stop)
