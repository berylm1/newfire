# 2026-06-02 - Minisforum Nightly Code Agent Deployment Plan

Status: **Direction corrected — agent should run on the NewFire Minisforum system, not on the Raspberry Pi**
Priority: **High / CEO request**
Project: [[NewFire Task Index|NewFire Tasks]]
Repository: https://github.com/berylm1/newfire
Target host: **NewFire Minisforum**
Target schedule: nightly, report delivered by **4:00 AM**

## Corrected instruction from Beryl

Beryl clarified that the agent should be created **on the system NewFire has on the Minisforum** and should perform the job description itself. Hermes on the Raspberry Pi should help set up, document, and coordinate — not act as the production NewFire nightly reviewer.

## Job description the Minisforum agent must perform

Every night, the agent should:

1. Check out or update the GitHub repo: `https://github.com/berylm1/newfire`.
2. Analyze the codebase for:
   - technical depth and likely bugs;
   - performance issues;
   - business-role implementation gaps;
   - orphaned, partial, or scaffolded features;
   - generic CRUD-only modules with weak domain logic;
   - disconnected or incomplete features;
   - incomplete end-to-end implementations.
3. Produce a clear report for Patrick/Beryl before 4:00 AM.
4. In Phase 1, stay **report-only**: no direct pushes, no main-branch changes, no silent deployments.
5. In Phase 2, if approved, create branches/PRs for targeted fixes instead of modifying production directly.

## Recommended deployment architecture

```text
GitHub repo: berylm1/newfire
        |
        v
NewFire Minisforum nightly agent
        |
        +--> local repo checkout
        +--> tests/lint/build/typecheck
        +--> codebase scans and AI review
        +--> Markdown/HTML report
        +--> email or Telegram delivery by 4:00 AM
```

## Phase 1 setup checklist on Minisforum

### 1. Connect to Minisforum

From Beryl's Dell or current terminal:

```bash
ssh <newfire-user>@<minisforum-host-or-ip>
```

### 2. Verify base tools

```bash
uname -a
whoami
pwd
git --version
python3 --version
node --version 2>/dev/null || true
npm --version 2>/dev/null || true
```

### 3. Set up GitHub access

Preferred options:

- SSH deploy key or user SSH key for `git@github.com:berylm1/newfire.git`
- or GitHub CLI/token if API access is needed

Verification command:

```bash
git ls-remote https://github.com/berylm1/newfire.git
```

If the repo is private, this will require auth.

### 4. Clone the repo into a dedicated agent workspace

```bash
mkdir -p ~/newfire-agent/workspace ~/newfire-agent/reports ~/newfire-agent/logs
cd ~/newfire-agent/workspace
git clone https://github.com/berylm1/newfire.git repo
```

### 5. Create a report-only nightly script

The script should:

- pull latest code;
- detect project stack and run available checks;
- scan for scaffold/TODO/orphan/generic CRUD patterns;
- ask the AI model to summarize risks and missing implementation areas;
- save report under `~/newfire-agent/reports/`;
- deliver the report to Patrick/Beryl.

### 6. Schedule after manual verification

Only after the manual run produces a useful report:

```bash
crontab -e
```

Example schedule:

```cron
0 4 * * * /home/<newfire-user>/newfire-agent/run-nightly-review.sh >> /home/<newfire-user>/newfire-agent/logs/cron.log 2>&1
```

## Safety boundaries

- The Minisforum agent should start report-only.
- It should not push to `main`.
- It should not deploy, migrate, or restart production services unless explicitly approved.
- If Phase 2 is enabled, it should work through short-lived branches and PRs.
- Secrets should live in environment/config files on the Minisforum, not in Obsidian or chat.

## Information still needed

- SSH hostname/IP for the NewFire Minisforum: `100.79.80.119`.
- Username on the Minisforum: `newwaveclaw`.
- SSH reachability from the Pi: **not yet verified** — initial test timed out on port 22.
- SSH reachability from Beryl's Mac: **confirmed** — Mac can connect to `newwaveclaw@100.79.80.119`.
- Minisforum diagnostics confirmed: Ubuntu 24.04 x86_64, git 2.43.0, Python 3.12.3, Node v22.22.2, npm 11.12.1, Docker 29.3.1.
- Repository access from Minisforum: **confirmed** — `git ls-remote https://github.com/berylm1/newfire.git` returned `main` and `feat/superlinked-rag-funmi`.
- Repository cloned on Minisforum to `/home/newwaveclaw/newfire-agent/workspace/repo`; current branch `main`, latest commit `500e979 openclaw: relax startup posture to allow no-AUD JWT signature mode`.
- Visible project areas include `openclaw/`, `newfire_backend_docker/`, `infra/`, `blueprint/`, `progress/`, and architecture documents.
- Initial repo inspection found Docker-focused components: `openclaw/docker-compose.yml`, `newfire_backend_docker/docker-compose.yml`, `progress/n8n_deploy/docker-compose.yml`, Python dependencies in `openclaw/requirements.txt`, and no top-level `package.json`/`pyproject.toml` detected in the first scan.
- Possible issue spotted for nightly audit: `progress/n8n_deploy/docker-compose.yml` output shows `DB_TYPE: postgresdb` mis-indented outside the `environment:` block, worth flagging in the first report.
- First Minisforum report generated at `/home/newwaveclaw/newfire-agent/reports/2026-06-03-0220-newfire-nightly-review.md`; v1 scanner works but is too noisy because it scans blueprint transcripts, SQL backup dumps, and YouTube metadata JSON.
- User pasted a very large YouTube `formats`/manifest JSON block from the report output, confirming `*.info.json` files are the main noise source and should be excluded from grep-style scans.
- Next improvement: filter large/reference/noisy files (`blueprint/*.vtt`, `blueprint/*.info.json`, `*.sql`, media files) and produce a shorter executive summary suitable for Patrick.
- Whether Hermes Agent, another coding agent, or a custom Python + LLM script should be the worker.
- Patrick's email address or preferred delivery channel.
- Which branch is the canonical nightly review target, likely `main` unless NewFire uses another production branch.
