from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class StorageConfig:
    path: str = "~/.netradar/data.db"
    retention_days: int = 7


@dataclass
class Thresholds:
    latency_ms: float = 100.0
    jitter_ms: float = 20.0
    packet_loss_pct: float = 5.0


@dataclass
class EndpointConfig:
    host: str
    name: str = ""
    thresholds: Thresholds | None = None

    def __post_init__(self):
        if not self.name:
            self.name = self.host


@dataclass
class Config:
    endpoints: list[EndpointConfig]
    interval: float = 5.0
    ping_count: int = 4
    jitter_window: int = 20
    thresholds: Thresholds = field(default_factory=Thresholds)
    storage: StorageConfig = field(default_factory=StorageConfig)


def load_config(path: str | Path) -> Config:
    with open(path) as f:
        data = yaml.safe_load(f)

    global_thresh = Thresholds(**data.get("thresholds", {}))

    endpoints = []
    for ep in data["endpoints"]:
        ep = dict(ep)
        ep_thresh = None
        if "thresholds" in ep:
            ep_thresh = Thresholds(**ep.pop("thresholds"))
        ep.setdefault("name", ep["host"])
        endpoints.append(EndpointConfig(
            host=ep["host"],
            name=ep["name"],
            thresholds=ep_thresh,
        ))

    storage = StorageConfig(**data.get("storage", {}))

    return Config(
        endpoints=endpoints,
        interval=data.get("interval", 5.0),
        ping_count=data.get("ping_count", 4),
        jitter_window=data.get("jitter_window", 20),
        thresholds=global_thresh,
        storage=storage,
    )
