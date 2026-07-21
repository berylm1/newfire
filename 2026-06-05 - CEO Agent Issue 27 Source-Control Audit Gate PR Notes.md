# 2026-06-05 - CEO Agent Issue 27 Source-Control Audit Gate PR Notes

## GitHub

- Issue: [#27 CEO gap: add full platform source-control manifest and audit gate](https://github.com/berylm1/newfire/issues/27)
- PR: [#31 docs: add source-control audit gate](https://github.com/berylm1/newfire/pull/31)
- Branch: `docs/issue-27-source-control-manifest`
- Commit: `1ed95c883c6c2a21ae4bc4915150bac8833e3971`
- Status: open, clean, mergeable; no GitHub checks configured.

## What changed

Added:

- `docs/ceo-agent/source-control-manifest.json`
- `scripts/check_source_control_manifest.py`

Updated:

- `backend-source.md`
- `docs/ceo-agent/README.md`

## Manifest result

The manifest currently lists 11 known NewFire surfaces.

Governed surfaces:

- `newfire-backend`
- `openclaw`
- `newfire-backend-docker`
- `infra-docs`

Strict blockers:

- `newfire-frontend`
- `nss-control`
- `nss-runner`
- `nss-portal`
- `nss-router`

Deferred scaffolds:

- `mcp-server`
- `client-sdk`

## Why this matters

This directly addresses the CEO blocker from issue #11: we cannot truthfully claim full platform auditability until every production/load-bearing service is either GitHub-tracked or has an approved vendored baseline.

The strict audit gate intentionally exits non-zero while blockers remain. That is the correct behavior: it prevents an agent from editing untracked production mirrors or claiming coverage for services that are not under PR governance.

## Verification

- `python3 -m json.tool docs/ceo-agent/source-control-manifest.json` passed.
- `python3 -m py_compile scripts/check_source_control_manifest.py` passed.
- `scripts/check_source_control_manifest.py --report-only` passed and reported 5 blockers.
- strict `scripts/check_source_control_manifest.py` exited `2` as expected while blockers remain.
- `git diff --check` passed.

No production deploys, restarts, migrations, load/chaos tests, or secret changes.

## CEO reporting angle

This advances lanes **A**, **B**, and **F**:

- A: codebase intelligence now has a machine-readable source-control map.
- B: product gap work now has a concrete gate for ungoverned services.
- F: readiness scoring can exclude or block surfaces without GitHub governance instead of guessing.

CEO-facing line:

> We added a source-control manifest and strict audit gate for the full NewFire platform. It confirms four surfaces are GitHub-governed and identifies five production/load-bearing blockers — frontend and NSS services — that must be brought under GitHub governance before we can truthfully report full-platform readiness.

## Next work

- Either verify/import the frontend source first, because it blocks E2E product reporting.
- Or continue with #28 onboarding, but label frontend source-control as a reporting blocker until resolved.
