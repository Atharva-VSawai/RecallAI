-- Phase 5: durable usage and operational telemetry.
create table if not exists usage_events (
    id uuid primary key default gen_random_uuid(),
    organization_id text not null,
    project_id text not null,
    user_id text,
    kind text not null check (kind in ('llm', 'embedding', 'transcription', 'query')),
    provider text not null,
    units bigint not null default 0,
    cost numeric(18,8) not null default 0,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists usage_events_project_created_idx on usage_events(project_id, created_at desc);
create index if not exists usage_events_user_created_idx on usage_events(user_id, created_at desc);

create table if not exists project_budgets (
    project_id text primary key,
    organization_id text not null,
    user_id text,
    cost_limit numeric(18,8) not null check (cost_limit >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists operational_metrics (
    id uuid primary key default gen_random_uuid(),
    organization_id text,
    project_id text,
    user_id text,
    name text not null,
    value numeric(18,8) not null default 1,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists operational_metrics_project_created_idx on operational_metrics(project_id, created_at desc);
