# TeslaTech — deployment & sync setup

This wires the **private home-server data** into the **public Streamlit app** without
ever exposing your server. Flow:

```
Home server (private)                Cloud (tiny)                 Streamlit Cloud (public)
─────────────────────                ────────────                 ────────────────────────
teslalogger-db  ──► etl/export ──►   Postgres: fleet_artifacts ──► reads cached, charts
  (21M rows)        anonymize         + contributions (survey)      Fleet Telemetry page
                    etl/publish  ──►  (optional) R2: fleet.json ──► Contribute page (writes)
   weekly cron, outbound only         a few hundred KB / week       visitors never hit your server
```

You only do steps 1–3 once. After that the weekly container keeps everything fresh.

---

## 1. Create the Supabase tables (one paste)

In your Supabase project → **SQL Editor** → New query → paste the contents of
[`deploy/supabase_schema.sql`](deploy/supabase_schema.sql) → **Run**.

That creates three tables with row-level-security so the *publishable* key can
read fleet/telemetry and submit questionnaire rows, while the *secret* key
publishes the weekly artifacts:

| Table | Holds | Written by | Read by |
|-------|-------|-----------|---------|
| `fleet_artifacts` | anonymized fleet summary (JSON) | ETL (secret key) | app (publishable) |
| `fleet_telemetry` | anonymized signal cloud (JSON) | ETL (secret key) | app (publishable) |
| `contributions` | public questionnaire rows | app (publishable) | app (publishable) |

Keys (Project → Settings → API):
- **Publishable** (`sb_publishable_…`) → goes in the Streamlit app (safe to expose).
- **Secret** (`sb_secret_…`) → only on the home server, in `deploy/.env`.

## 2. Deploy the weekly sync on Unraid

`deploy/.env` is already filled with your Supabase URL + secret key and a salt.
Pin the salt and keep the file private (it is gitignored). Then:

```bash
docker compose -f deploy/docker-compose.sync.yml --env-file deploy/.env up -d --build
```

The container reads `teslalogger-db` directly, exports both the fleet summary and
the telemetry cloud, anonymizes them, and upserts both into Supabase weekly.

The container joins `teslalogger_default`, reads `teslalogger-db` directly, writes the
anonymized artifact to Postgres weekly, and restarts on boot. Run once immediately with:

```bash
docker compose -f deploy/docker-compose.sync.yml --env-file deploy/.env run --rm \
  -e RUN_MODE=once teslatech-sync
```

Verify privacy before trusting it: `etl/anonymize.py` drops every PII field and
hashes car ids under your salt. The artifact contains only physics (model, pack,
chemistry, motors, SOH, efficiency, charging) — no names, VINs, GPS or addresses.

## 3. Point the Streamlit app at Supabase

In Streamlit Community Cloud → app → **Settings → Secrets** (this is exactly the
local `streamlit_repo/.streamlit/secrets.toml`):

```toml
[supabase]
url = "https://zdjblsovpdiqcebjnryq.supabase.co"
publishable_key = "sb_publishable_…"
```

That's it. **Fleet Telemetry** and **Telemetry Explorer** read the latest artifacts;
**Contribute** writes submissions — all via the publishable key under RLS. Everything
is cached (`st.cache_data`, 1 h) so visitor traffic stays flat. The secret key never
leaves your server.

> Security: the secret key was shared in chat — rotate it in Supabase → Settings →
> API once the sync is confirmed working, and update `deploy/.env`.

### Optional: serve telemetry from Cloudflare R2 (for scale)

The telemetry cloud is the largest artifact (a few MB). If Supabase egress becomes a
concern, push it to R2 instead: fill the `S3_*` vars in `deploy/.env`, set
`PUBLISH_TARGETS="supabase s3"`, and add `[telemetry] url = "https://…/telemetry.json"`
to Streamlit secrets. The loader prefers Supabase, then the URL, then a local file.

---

## Local development

```bash
python -m venv .venv && .venv/Scripts/pip install -r deploy/requirements.sync.txt streamlit plotly
# produce an artifact from the live DB over SSH (no direct DB access needed):
SSH_PASS=... TESLATECH_ANON_SALT=dev TESLATECH_DB_MODE=ssh python -m etl.export_fleet --out artifacts
cp artifacts/fleet.json streamlit_repo/data/fleet.json     # bundle for the app
streamlit run streamlit_repo/Dashboard.py                  # open the Fleet Telemetry page
```
