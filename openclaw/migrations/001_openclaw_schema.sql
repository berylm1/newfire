-- OpenClaw v1 schema (mirrors spec section 4).
-- Idempotent: safe to re-run.

create schema if not exists openclaw;

create table if not exists openclaw.developers (
  email          text primary key,
  display_name   text,
  first_seen_at  timestamptz not null default now(),
  last_seen_at   timestamptz not null default now()
);

create table if not exists openclaw.projects (
  id           bigserial primary key,
  owner_email  text not null references openclaw.developers(email),
  name         text not null,
  template     text not null,
  cephfs_path  text not null,
  created_at   timestamptz not null default now(),
  destroyed_at timestamptz,
  unique (owner_email, name)
);

create table if not exists openclaw.dispatches (
  id             bigserial primary key,
  owner_email    text not null,
  project_id     bigint references openclaw.projects(id),
  prompt_snippet text not null,
  picked_tool    text not null check (picked_tool in ('openhands','opencode','direct')),
  picked_reason  text not null,
  override_tool  text,
  created_at     timestamptz not null default now()
);

create table if not exists openclaw.usage (
  id                bigserial primary key,
  owner_email       text not null,
  project_id        bigint,
  tool              text not null,
  model             text not null,
  prompt_tokens     int  not null,
  completion_tokens int  not null,
  latency_ms        int  not null,
  ts                timestamptz not null default now()
);

create index if not exists usage_owner_ts_idx on openclaw.usage (owner_email, ts);
create index if not exists usage_model_ts_idx on openclaw.usage (model, ts);
create index if not exists dispatches_owner_ts_idx on openclaw.dispatches (owner_email, created_at);

-- Grant on schema so the newfire role (used by openclaw container) can read/write.
grant usage on schema openclaw to newfire;
grant all privileges on all tables in schema openclaw to newfire;
grant all privileges on all sequences in schema openclaw to newfire;
alter default privileges in schema openclaw grant all on tables to newfire;
alter default privileges in schema openclaw grant all on sequences to newfire;
