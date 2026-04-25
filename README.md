# netradar

Hálózati stabilitás monitor. Valós időben méri az összes konfigurált endpoint latenciáját, jitterét és csomagveszteségét. Futhat CLI TUI-ként, háttérben daemonként (SQLite historikus tárolással), vagy macOS menüsávban.

## Telepítés

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Parancsok

### `monitor` — live TUI

```bash
.venv/bin/python -m netradar monitor
```

| Flag | Leírás |
|------|--------|
| `-c, --config PATH` | Config fájl (alapértelmezett: `config.yaml`) |
| `-i, --interval FLOAT` | Mérési intervallum másodpercben |
| `--no-alerts` | macOS értesítések kikapcsolása |

### `daemon` — háttérfolyamat

Headless mérési loop, minden eredményt SQLite-ba ment.

```bash
.venv/bin/python -m netradar daemon
```

### `menubar` — macOS menüsáv

Pollozza a SQLite DB-t, és mutatja az aktuális státuszt. A daemon-nak párhuzamosan kell futnia.

```bash
.venv/bin/python -m netradar menubar
```

A menüsáv ikon a legrosszabb endpoint állapotát tükrözi:

| Ikon | Jelentés |
|------|----------|
| `●` | Minden endpoint OK |
| `⚠` | Legalább egy endpoint WARN |
| `✕` | Legalább egy endpoint DOWN |

### `install` / `uninstall` — launchd integráció

Automatikus daemon indítás loginkor:

```bash
.venv/bin/python -m netradar install    # telepít + azonnal elindít
.venv/bin/python -m netradar uninstall  # leállít + eltávolít
```

## Konfiguráció

```yaml
storage:
  path: "~/.netradar/data.db"  # SQLite adatbázis helye
  retention_days: 7             # hány napig őrizze a méréseket

interval: 5       # másodperc mérési körök között
ping_count: 4     # ping darabszám köröként
jitter_window: 20 # rolling ablak mérete a jitter számításhoz

thresholds:       # globális alapértelmezés
  latency_ms: 100
  jitter_ms: 20
  packet_loss_pct: 5

endpoints:
  - name: Google DNS
    host: 8.8.8.8
  - name: Gateway
    host: 192.168.1.1
    thresholds:     # endpoint-specifikus felülírás
      latency_ms: 5
      jitter_ms: 2
      packet_loss_pct: 0
```

## Mérőszámok

- **Latency** – átlagos round-trip idő az adott mérési körben (ms)
- **Min / Max** – legkisebb és legnagyobb RTT a körben
- **Jitter** – az utolsó `jitter_window` darab átlag-RTT szórása (ms); a kapcsolat stabilitásának fő mutatója
- **Loss** – csomagveszteség az adott körben (%)
- **History** – sparkline grafikon az utolsó 20 mérésről (csak TUI)

## Alertek

Ha egy endpoint latenciája, jittere vagy csomagvesztesége meghaladja a küszöbértéket, macOS rendszerértesítés jelenik meg. Ugyanarra az endpointra 60 másodpercenként legfeljebb egy értesítés küldődik.

## Projekt struktúra

```
netradar/
├── config.yaml           # konfiguráció
├── requirements.txt
└── netradar/
    ├── __main__.py       # CLI belépőpont (subcommandok)
    ├── config.py         # konfiguráció + StorageConfig
    ├── monitor.py        # ping mérés + statisztikák
    ├── storage.py        # SQLite réteg
    ├── daemon.py         # headless mérési loop
    ├── menubar.py        # macOS menüsáv (rumps)
    ├── display.py        # Rich TUI táblázat
    └── alert.py          # macOS értesítések
```
