# TeslaTech — measured fleet meets the crowd

TeslaTech turns a private, continuously-logged Teslalogger database into **public,
anonymized, scientific battery intelligence** inside the
[teslatech.streamlit.app](https://teslatech.streamlit.app) app — and lets the world
contribute their own data back.

It joins two halves that nobody else has together:

- **Measurement** — a real fleet logged second-by-second (SOH, charging, efficiency).
- **Knowledge** — the reference brain (battery chronology, chemistries, WLTP,
  consumption constants, motor/vehicle intelligence) that *interprets* those numbers.

## How it fits together

```
Home server (private)              Cloud (tiny)                Streamlit (public)
  teslalogger-db                     Postgres                    Fleet Telemetry page
   → etl/export_fleet  ──anonymize──► fleet_artifacts ──cached──► SOH curves, efficiency,
   → etl/publish                      contributions  ◄──writes──   benchmarking
  weekly cron, outbound only          (survey)                    Contribute page
```

Your server is never exposed; only a few hundred KB of anonymized physics leave it
each week. See [SETUP.md](SETUP.md) for deployment.

## Repository layout

| Path | What it is |
|------|------------|
| `etl/vin.py` | Tesla VIN decoder (plant / year / model — no serial) |
| `etl/identity.py` | Resolve a car → public identity via the knowledge brain |
| `etl/analytics.py` | Scientific SOH, charging, efficiency |
| `etl/anonymize.py` | Privacy layer (salted-hash ids, PII guard) |
| `etl/export_fleet.py` | Read DB → anonymized `fleet.json` artifact |
| `etl/publish.py` | Push the artifact to Postgres / R2 |
| `etl/db.py` | Read-only DB access (direct on server, SSH in dev) |
| `etl/telemetry.py` + `export_telemetry.py` | Anonymized downsampled signal cloud |
| `etl/publish.py` | Push artifacts to Supabase / Postgres / R2 |
| `streamlit_repo/pages/04_Fleet_Telemetry.py` | Public fleet page (SOH, efficiency, benchmark) |
| `streamlit_repo/pages/05_Contribute.py` | Public questionnaire (replaces Google Sheets) |
| `streamlit_repo/pages/06_Telemetry_Explorer.py` | Power/torque vs SOC & temp scatter explorer |
| `streamlit_repo/src/data/fleet.py` / `telemetry.py` | Artifact loaders (Supabase / URL / local) |
| `streamlit_repo/src/data/benchmark.py` | Car-vs-world benchmarking |
| `streamlit_repo/src/data/contributions.py` | Submission store (Supabase / SQLite) |
| `streamlit_repo/src/data/supabase_client.py` | Minimal Supabase REST client (publishable key) |
| `deploy/` | Sync container + `supabase_schema.sql` |
| `tests/test_etl.py` | Unit tests for the ETL core |

## The privacy contract (enforced in code)

The world sees physics, never you. `etl/anonymize.py` derives a stable, irreversible
car id (HMAC under a private salt), and `assert_clean()` refuses to emit any record
containing a name, VIN, GPS coordinate, address or token. VINs are decoded locally and
discarded; no location data is ever aggregated or shipped.

## What it shows

- **State-of-Health over time** — robust BMS full-pack ÷ design capacity, per chemistry.
- **Degradation vs distance** — every pack on the SOH/odometer plane.
- **Real-world efficiency** — measured Wh/km vs factory constant + the temperature curve.
- **Charging fingerprint** — DC/AC split, peak power.
- **Benchmark a car** — vs Tesla's published retention curve and the population.
- **Telemetry explorer** — max discharge / battery / motor power and torque vs SOC,
  speed and cell temperature (colour = temp, size = SOC), in the spirit of the old
  TeslaTech / ScanMyTesla scatter views.

## Develop

```bash
python -m venv .venv && .venv/Scripts/pip install -r deploy/requirements.sync.txt streamlit plotly pytest
.venv/Scripts/python -m pytest tests/ -q
SSH_PASS=... TESLATECH_ANON_SALT=dev python -m etl.export_fleet --out artifacts
cp artifacts/fleet.json streamlit_repo/data/fleet.json
streamlit run streamlit_repo/Dashboard.py
```
