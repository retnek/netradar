# netradar

Hálózati stabilitás monitor CLI. Valós időben méri az összes konfigurált endpoint latenciáját, jitterét és csomagveszteségét, és macOS értesítést küld, ha valami küszöbérték fölé megy.

## Telepítés

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Indítás

```bash
.venv/bin/python -m netradar
```

Opciók:

| Flag | Leírás |
|------|--------|
| `-c, --config PATH` | Config fájl elérési útja (alapértelmezett: `config.yaml`) |
| `-i, --interval FLOAT` | Mérési intervallum másodpercben (felülírja a config értékét) |
| `--no-alerts` | macOS értesítések kikapcsolása |

## Konfiguráció

A `config.yaml` fájlban adhatók meg az endpointok és a küszöbértékek.

```yaml
interval: 5          # másodperc mérési körök között
ping_count: 4        # ping darabszám köröként
jitter_window: 20    # rolling ablak mérete a jitter számításhoz

thresholds:          # globális alapértelmezés
  latency_ms: 100
  jitter_ms: 20
  packet_loss_pct: 5

endpoints:
  - name: Google DNS
    host: 8.8.8.8
  - name: Gateway
    host: 192.168.1.1
    thresholds:       # endpoint-specifikus felülírás
      latency_ms: 5
      jitter_ms: 2
      packet_loss_pct: 0
```

## Mérőszámok

- **Latency** – átlagos round-trip idő az adott mérési körben (ms)
- **Min / Max** – legkisebb és legnagyobb RTT a körben
- **Jitter** – az utolsó `jitter_window` darab átlag-RTT szórása (ms); az összeköttetés stabilitásának fő mutatója
- **Loss** – csomagveszteség az adott körben (%)
- **History** – sparkline grafikon az utolsó 20 mérésről

## Alertek

Ha egy endpoint latenciája, jittere vagy csomagvesztesége meghaladja a küszöbértéket, macOS rendszerértesítés jelenik meg. Ugyanarra az endpointra 60 másodpercenként legfeljebb egy értesítés küldődik.

## Projekt struktúra

```
netradar/
├── config.yaml          # konfiguráció
├── requirements.txt
└── netradar/
    ├── __main__.py      # CLI belépőpont
    ├── config.py        # konfiguráció betöltése
    ├── monitor.py       # ping mérés + statisztikák
    ├── display.py       # Rich TUI táblázat
    └── alert.py         # macOS értesítések
```
