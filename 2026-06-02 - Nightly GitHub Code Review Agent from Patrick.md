# 2026-06-02 - Nightly GitHub Code Review Agent from Patrick

Status: **Direction corrected — deploy the actual nightly agent on the NewFire Minisforum system**
Priority: **High / CEO request**
Project: [[NewFire Mission and May 1 Goal|NewFire]]
Captured: 2026-06-02 17:31 EDT
Requested by: Mr Patrick / CEO
Owner: Beryl + NewFire Minisforum agent, with Hermes assisting setup/documentation
Repository: `https://github.com/berylm1/newfire`
Target delivery: nightly report routed to Patrick's email by **4:00 AM**

## Original request

> From Mr Patrick: i need to you create an agent the check code out of github analyze it for (a) technical depth -bugs (b) performance issue (c) fully implement business roles (d) search for orphan, partially and generic scaffolded features across the platform - fully implement them end to end -generic CRUD-only patterns , modules with no domain logic, disconnected features, and incomplete implementations. work on the agentic features that runs every night to review code in github and send update by the time i wake up

## Task summary

Build or configure a **nightly NewFire GitHub code-review / implementation agent** that:

1. Checks out the NewFire GitHub repository.
2. Analyzes the codebase for:
   - technical depth and likely bugs;
   - performance issues;
   - whether business roles are fully implemented;
   - orphaned, partial, or scaffolded features;
   - generic CRUD-only patterns with no domain logic;
   - disconnected modules/features;
   - incomplete end-to-end implementations.
3. Produces a nightly executive/engineering report.
4. Sends the report to Patrick's email by **4:00 AM**.
5. Eventually can go beyond review into implementation work, but only inside a controlled workflow with branches, tests, and review before merge.

## Initial implementation direction

Use a safe two-phase approach:

### Phase 1 — nightly audit/report only

The first version should **not auto-merge code**. It should:

- clone or pull the GitHub repo;
- inspect git diff/status and current branch;
- run tests, type checks, linting, and build checks if available;
- scan for TODO/FIXME/stub/scaffold patterns;
- inspect modules/routes/services for disconnected features;
- identify generic CRUD endpoints that lack business-domain logic;
- produce a report grouped by severity and area;
- email Patrick by 4:00 AM.

### Phase 2 — agentic implementation workflow

After the audit agent is stable, add controlled implementation:

- create a new branch per improvement batch;
- make small targeted changes;
- run tests/build;
- open PRs instead of pushing directly to main;
- include a summary of changes, risks, and remaining manual review items.

## Implementation log

### 2026-06-02 — Direction corrected: production agent belongs on Minisforum

Beryl provided the GitHub repo: `https://github.com/berylm1/newfire`.

Beryl clarified that Hermes on the Raspberry Pi should **not** be the production nightly reviewer. The actual agent should be created and run on the NewFire Minisforum system, where NewFire's system environment lives.

Actions taken on the Pi:

- Paused the temporary Pi-based Hermes cron job `20c12b375fae` so it does not pretend to be the production NewFire agent.
- Created deployment note: [[2026-06-02 - Minisforum Nightly Code Agent Deployment Plan]].
- Kept the earlier Pi scaffold as reference material only.

### 2026-06-02 — Phase 1 scaffold created

Hermes created a report-only audit scaffold on the Pi.

Created files:

- Script: `/home/beryl/.hermes/scripts/newfire_nightly_github_audit.py`
- Config template: `/home/beryl/.hermes/newfire-audit/config.example.json`
- Report folder: `Projects/NewFire/Nightly Code Reviews/`
- First blocked/preflight report: [[../Nightly Code Reviews/2026-06-02-2110-newfire-nightly-code-audit|2026-06-02-2110-newfire-nightly-code-audit]]

Created Hermes cron job:

- Job ID: `20c12b375fae`
- Name: `NewFire nightly GitHub code audit (report-only preflight)`
- Schedule: `0 4 * * *` — daily at 4:00 AM
- Delivery: current Telegram chat / origin for now
- Mode: report-only/preflight; no code modifications, no pushes, no PRs, no Patrick email yet

Discovery results:

- `git` is installed.
- `gh` GitHub CLI is not installed.
- `himalaya` email CLI is not installed/configured.
- No GitHub token or git credential for GitHub was found in the Pi checks.
- No NewFire repo clone was found on the Pi; only unrelated repos were found (`hermes-agent`, `llama.cpp`, Codex sandbox, etc.).

Script capabilities:

- clone/pull configured GitHub repo;
- inspect git branch/status/recent commits;
- detect and run available `npm`/Python/Go/Rust test/build/lint commands;
- scan for TODO/FIXME/stub/scaffold/placeholder markers;
- scan for mock/demo leftovers;
- scan for auth/role/RBAC areas;
- scan for performance hotspot markers;
- scan for potential secrets/security strings;
- detect possible generic CRUD-heavy/domain-light files;
- detect possible orphan/disconnected feature candidates;
- write Markdown reports into Obsidian.

Required config file when ready:

```json
{
  "repo_url": "https://github.com/OWNER/REPO.git",
  "branch": "main",
  "workdir": "/home/beryl/newfire-audit/repo",
  "report_dir": "/home/beryl/Obsidian vault/Projects/NewFire/Nightly Code Reviews",
  "patrick_email": "patrick@example.com"
}
```

Copy the template into place:

```bash
mkdir -p /home/beryl/.hermes/newfire-audit
cp /home/beryl/.hermes/newfire-audit/config.example.json /home/beryl/.hermes/newfire-audit/config.json
```

Then fill in the repo URL and Patrick email.

## Report sections Patrick likely wants

- Executive summary: what changed / what needs attention.
- Critical bugs or broken flows.
- Performance concerns.
- Business-role implementation gaps.
- Orphaned or disconnected features.
- Generic CRUD-only modules needing real domain logic.
- Partially implemented/scaffolded features.
- Tests/build status.
- Recommended next implementation targets.
- Any PRs/branches created, if Phase 2 is enabled.

## Required information before scheduling the 4 AM email

- Patrick's email address.
- Which NewFire GitHub repository should be used.
- Whether Hermes already has GitHub access to that repo from this machine.
- Which branch should be reviewed nightly.
- Whether the first nightly run should be report-only or allowed to open PRs.
- Email sending mechanism:
  - currently, the `himalaya` email CLI does not appear to be installed/configured on this Pi, so email routing needs setup or another delivery path.

## Suggested immediate next steps tonight

1. Confirm Patrick's email address.
2. Confirm repo URL and branch.
3. Verify GitHub access from the Pi or DGX Spark.
4. Create a first report-only nightly cron job.
5. Run the job once manually and send Beryl the output for approval.
6. If approved, schedule daily 4:00 AM delivery to Patrick.

## Safety notes

- Do not let the first version silently modify production code or push to main.
- Any auto-implementation should go through branches/PRs with tests.
- Keep NewFire production architecture documented in both GitHub and Obsidian when changes are made.
