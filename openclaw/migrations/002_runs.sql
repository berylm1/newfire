-- Runs table for OpenClaw execute mode (PR 2).
-- One row per /v1/dispatch with execute=true.
create table if not exists openclaw.runs (
  id            bigserial primary key,
  dispatch_id   bigint not null references openclaw.dispatches(id) on delete cascade,
  owner_email   text not null,
  tool          text not null,
  model         text,
  prompt        text not null,
  status        text not null default 'pending' check (status in ('pending','running','succeeded','failed','timeout')),
  output        text,
  error         text,
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  duration_ms   int,
  tokens_in     int,
  tokens_out    int
);

create index if not exists runs_owner_started_idx on openclaw.runs (owner_email, started_at desc);
create index if not exists runs_dispatch_idx on openclaw.runs (dispatch_id);
create index if not exists runs_status_idx on openclaw.runs (status);

grant all privileges on openclaw.runs to newfire;
grant all privileges on openclaw.runs_id_seq to newfire;
