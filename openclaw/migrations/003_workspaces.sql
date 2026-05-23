-- Workspaces + truncation tracking for OpenClaw v1 PR 3.
alter table openclaw.runs
  add column if not exists workspace_path text,
  add column if not exists files_written  jsonb,
  add column if not exists finish_reason  text,
  add column if not exists truncated      boolean default false;

create index if not exists runs_truncated_idx on openclaw.runs (truncated)
  where truncated is true;
