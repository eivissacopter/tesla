-- TeslaTech — Supabase schema. Run once in the Supabase SQL Editor.
-- Creates the two tables and row-level-security policies so that:
--   * the publishable (anon) key can READ fleet data and SUBMIT contributions
--   * the secret (service_role) key bypasses RLS to publish the weekly artifact

-- ---------------------------------------------------------------------------
-- Anonymized fleet artifact (one row per weekly data_version)
-- ---------------------------------------------------------------------------
create table if not exists public.fleet_artifacts (
    data_version text primary key,
    published_at timestamptz not null default now(),
    payload      jsonb       not null
);

alter table public.fleet_artifacts enable row level security;

drop policy if exists "fleet read for anon" on public.fleet_artifacts;
create policy "fleet read for anon"
    on public.fleet_artifacts for select
    to anon, authenticated
    using (true);
-- No insert/update policy for anon: only the secret key (service_role) may write.

-- ---------------------------------------------------------------------------
-- Anonymized telemetry cloud (one row per weekly data_version)
-- Larger payload; only the Telemetry Explorer page reads it.
-- ---------------------------------------------------------------------------
create table if not exists public.fleet_telemetry (
    data_version text primary key,
    published_at timestamptz not null default now(),
    payload      jsonb       not null
);

alter table public.fleet_telemetry enable row level security;

drop policy if exists "telemetry read for anon" on public.fleet_telemetry;
create policy "telemetry read for anon"
    on public.fleet_telemetry for select
    to anon, authenticated
    using (true);

-- ---------------------------------------------------------------------------
-- Public questionnaire submissions (replaces Google Sheets)
-- ---------------------------------------------------------------------------
create table if not exists public.contributions (
    id               bigint generated always as identity primary key,
    submitted_at     timestamptz not null default now(),
    username         text,
    model            text,
    trim             text,
    drivetrain       text,
    battery          text,
    chemistry        text,
    origin           text,
    model_year       int,
    age_months       double precision,
    odometer_km      double precision,
    rated_range_km   double precision,
    capacity_net_kwh double precision,
    cycles           double precision,
    daily_soc_limit  double precision,
    dc_ratio         double precision,
    degradation_pct  double precision,
    software         text,
    notes            text,
    source           text default 'questionnaire'
);

alter table public.contributions enable row level security;

drop policy if exists "contrib read for anon" on public.contributions;
create policy "contrib read for anon"
    on public.contributions for select
    to anon, authenticated
    using (true);

drop policy if exists "contrib insert for anon" on public.contributions;
create policy "contrib insert for anon"
    on public.contributions for insert
    to anon, authenticated
    with check (true);
