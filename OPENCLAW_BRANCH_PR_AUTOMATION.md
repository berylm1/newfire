# OpenClaw Branch and PR Automation Plan

**Version:** 1.0  
**Parent:** [OPENCLAW_GITHUB_CONTROL_PLANE.md](./OPENCLAW_GITHUB_CONTROL_PLANE.md)  
**Issue:** #22  

---

## Overview

This document outlines the safe implementation plan for OpenClaw branch and PR automation, including source-control preflight checks and the approval workflow required before any code changes.

---

## Automation Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PR AUTOMATION FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Finding/   │───▶│  Write Mode │───▶│  Preflight  │───▶│   Branch    │        │
│  │  Fix        │    │  Approved?  │    │  Check      │    │  Created    │        │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
│                            │                    │                   │              │
│                     ┌──────┴──────┐             │                   │              │
│                     │ No: STOP   │             │                   │              │
│                     │ Report only│             │                   │              │
│                     └────────────┘             │                   │              │
│                                                 │                   │              │
│                                                 ▼                   ▼              │
│                                        ┌─────────────────────────────┐           │
│                                        │   Implementation            │           │
│                                        │   - Write code             │           │
│                                        │   - Add tests              │           │
│                                        │   - Document changes       │           │
│                                        └─────────────┬───────────────┘           │
│                                                      │                            │
│                                                      ▼                            │
│                                        ┌─────────────────────────────┐           │
│                                        │   Commit & Push            │           │
│                                        │   - Sign commits           │           │
│                                        │   - Clear commit message   │           │
│                                        └─────────────┬───────────────┘           │
│                                                      │                            │
│                                                      ▼                            │
│                                        ┌─────────────────────────────┐           │
│                                        │   Create PR                 │           │
│                                        │   - Fill template           │           │
│                                        │   - Link to issue           │           │
│                                        │   - Request review          │           │
│                                        └─────────────┬───────────────┘           │
│                                                      │                            │
│                                                      ▼                            │
│                                        ┌─────────────────────────────┐           │
│                                        │   Human Review             │◀──────────┤
│                                        │   - Review changes         │           │
│                                        │   - Approve or Request     │           │
│                                        │     changes                 │           │
│                                        └─────────────┬───────────────┘           │
│                                                      │                            │
│                              ┌────────────────────────┼────────────────────────┐  │
│                              │                        │                        │  │
│                              ▼                        ▼                        │  │
│                     ┌─────────────┐          ┌─────────────┐         ┌────────┐ │
│                     │  Approved   │          │  Changes    │         │ Rejected│ │
│                     │  Merge PR   │          │  Requested  │────────▶│ Close  │ │
│                     └─────────────┘          └──────┬──────┘         └────────┘ │
│                                                       │                        │
│                                                       │                        │
│                                                       ▼                        │
│                                              Implement feedback                │
│                                              and repeat cycle                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Preflight Check System

### Source Control Verification

Before any code modification, the following preflight checks must pass:

#### 1. Repository Verification

```bash
# Check repository exists and is accessible
gh repo view owner/repo --json name,url,isArchived,visibility

# Verify it's not archived
if [ "$(gh repo view owner/repo --jq '.isArchived')" = "true" ]; then
  echo "ERROR: Repository is archived"
  exit 1
fi

# Verify it's not a fork (unless explicitly approved)
if [ "$(gh repo view owner/repo --jq '.isFork')" = "true" ]; then
  echo "WARNING: Repository is a fork"
fi
```

#### 2. Authentication Check

```bash
# Verify GitHub token has appropriate permissions
gh api user --jq '.login'

# Check repository permissions
gh api repos/owner/repo/collaborators --jq \
  '.[] | select(.login == "openhands") | .permissions'
```

#### 3. Branch Protection Check

```bash
# Get main branch protection status
gh api repos/owner/repo/branches/main/protection --jq '{
  required_status_checks,
  enforce_admins,
  required_reviewers,
  restrictions
}'

# Check if we can push to main (should be false)
CAN_PUSH_MAIN=$(gh api repos/owner/repo/branches/main/protection --jq '.allow_force_pushes // false')
if [ "$CAN_PUSH_MAIN" = "true" ]; then
  echo "WARNING: Main branch allows force pushes"
fi
```

#### 4. Git Status Check

```bash
# Ensure working directory is clean
git status

# Verify we're on the correct base branch
git branch --show-current

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
  echo "WARNING: Uncommitted changes detected"
fi
```

### Preflight Script

```python
#!/usr/bin/env python3
"""
OpenClaw Preflight Check Script

Performs source-control verification before any code modifications.
"""

import subprocess
import sys
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class PreflightResult:
    """Result of a preflight check."""
    check_name: str
    passed: bool
    message: str
    blocking: bool = True


class PreflightChecker:
    """Performs preflight checks for GitHub operations."""
    
    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.full_name = f"{owner}/{repo}"
        self.results: list[PreflightResult] = []
    
    def run_command(self, cmd: list[str]) -> tuple[int, str, str]:
        """Run a shell command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)
    
    def check_gh_installed(self) -> bool:
        """Verify GitHub CLI is installed."""
        code, _, _ = self.run_command(["which", "gh"])
        return code == 0
    
    def check_repo_exists(self) -> PreflightResult:
        """Verify repository exists and is accessible."""
        code, output, _ = self.run_command([
            "gh", "api", f"repos/{self.full_name}", "--jq", "."
        ])
        
        if code != 0:
            return PreflightResult(
                check_name="Repository Access",
                passed=False,
                message=f"Cannot access repository: {output}",
                blocking=True
            )
        
        try:
            data = json.loads(output)
            is_archived = data.get("is_archived", False)
            is_fork = data.get("is_fork", False)
            
            if is_archived:
                return PreflightResult(
                    check_name="Repository Status",
                    passed=False,
                    message="Repository is archived",
                    blocking=True
                )
            
            msg = f"Repository accessible: {data.get('full_name')}"
            if is_fork:
                msg += " (fork)"
            
            return PreflightResult(
                check_name="Repository Access",
                passed=True,
                message=msg,
                blocking=False
            )
        except json.JSONDecodeError:
            return PreflightResult(
                check_name="Repository Response",
                passed=False,
                message="Invalid response from GitHub API",
                blocking=True
            )
    
    def check_branch_protection(self) -> PreflightResult:
        """Verify branch protection rules."""
        code, output, _ = self.run_command([
            "gh", "api", f"repos/{self.full_name}/branches/main/protection",
            "--jq", "."
        ])
        
        if code != 0:
            # Main branch might not exist, check for default branch
            code, default, _ = self.run_command([
                "gh", "api", f"repos/{self.full_name}",
                "--jq", ".default_branch"
            ])
            branch = default if code == 0 else "main"
            
            code, output, _ = self.run_command([
                "gh", "api", f"repos/{self.full_name}/branches/{branch}/protection",
                "--jq", "."
            ])
        
        if code == 0:
            try:
                protection = json.loads(output)
                allow_force = protection.get("allow_force_pushes", False)
                
                if allow_force:
                    return PreflightResult(
                        check_name="Branch Protection",
                        passed=True,
                        message="Force pushes allowed (non-blocking warning)",
                        blocking=False
                    )
                
                return PreflightResult(
                    check_name="Branch Protection",
                    passed=True,
                    message="Branch protection enabled",
                    blocking=False
                )
            except json.JSONDecodeError:
                pass
        
        return PreflightResult(
            check_name="Branch Protection",
            passed=True,
            message="No branch protection found or unable to check",
            blocking=False
        )
    
    def check_write_permission(self) -> PreflightResult:
        """Verify we have write permission (for PR creation)."""
        code, output, _ = self.run_command([
            "gh", "api", f"repos/{self.full_name}/collaborations",
            "--jq", ".[].permissions"
        ])
        
        # If we can't check, assume read-only
        if code != 0:
            return PreflightResult(
                check_name="Write Permission",
                passed=True,
                message="Unable to verify write permission (may be read-only)",
                blocking=False
            )
        
        return PreflightResult(
            check_name="Write Permission",
            passed=True,
            message="Write permission verified",
            blocking=False
        )
    
    def run_all_checks(self) -> bool:
        """Run all preflight checks. Returns True if all pass."""
        if not self.check_gh_installed():
            print("ERROR: GitHub CLI (gh) is not installed")
            return False
        
        checks = [
            self.check_repo_exists,
            self.check_branch_protection,
            self.check_write_permission,
        ]
        
        all_passed = True
        for check in checks:
            result = check()
            self.results.append(result)
            status = "✓" if result.passed else "✗"
            blocking = " [BLOCKING]" if result.blocking else ""
            print(f"{status} {result.check_name}: {result.message}{blocking}")
            
            if not result.passed and result.blocking:
                all_passed = False
        
        return all_passed


def main():
    if len(sys.argv) < 3:
        print("Usage: preflight_check.py <owner> <repo>")
        sys.exit(1)
    
    owner, repo = sys.argv[1], sys.argv[2]
    checker = PreflightChecker(owner, repo)
    
    if checker.run_all_checks():
        print("\n✓ All preflight checks passed")
        sys.exit(0)
    else:
        print("\n✗ Preflight checks failed - blocking modifications")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Approval Workflow

### Approval Requirements

Before any code modification, explicit approval is required through GitHub issue comments:

#### Level 1: Write Mode Approval

For creating branches and submitting PRs:

```
@openhands approve write mode

This approves the agent to:
- Create feature branches
- Commit code changes
- Push to feature branches
- Create pull requests

NOT approved:
- Direct main branch pushes
- Production deployments
- Secret modifications
```

#### Level 2: Production Approval

For production-affecting changes:

```
@openhands approve production

This additionally approves:
- Production deployments
- Database migrations
- Service restarts
- Secret modifications
```

### Approval Verification

```python
def check_write_approval(issue_number: int, owner: str, repo: str) -> bool:
    """Check if issue has write mode approval."""
    code, output, _ = run_command([
        "gh", "api", f"repos/{owner}/{repo}/issues/{issue_number}/comments",
        "--jq", ".[].body"
    ])
    
    if code != 0:
        return False
    
    approval_patterns = [
        "approve write mode",
        "write mode approved",
        "agent:write-approved"
    ]
    
    return any(
        pattern.lower() in comment.lower()
        for comment in output.split("\n")
        for pattern in approval_patterns
    )
```

---

## Branch Automation

### Branch Naming Convention

All agent-created branches must follow this pattern:

```
openhands/{issue-number}-{short-description}
```

Examples:
- `openhands/22-github-control-plane`
- `openhands/11-add-gap-analysis`
- `openhands/17-cors-hardening`

### Branch Creation Process

```python
def create_feature_branch(
    owner: str,
    repo: str,
    issue_number: int,
    description: str,
    base_branch: str = "main"
) -> str:
    """
    Create a feature branch for an issue fix.
    
    Returns the branch name on success, raises on failure.
    """
    # Sanitize description
    short_desc = (
        description.lower()
        .replace(" ", "-")
        .replace("_", "-")
        .replace("/", "-")[:50]
    )
    
    branch_name = f"openhands/{issue_number}-{short_desc}"
    
    # Verify we're in a git repository
    code, _, _ = run_command(["git", "rev-parse", "--git-dir"])
    if code != 0:
        raise RuntimeError("Not in a git repository")
    
    # Fetch latest from remote
    run_command(["git", "fetch", "origin", base_branch])
    
    # Create branch
    code, _, err = run_command([
        "git", "checkout", "-b", branch_name, f"origin/{base_branch}"
    ])
    
    if code != 0:
        raise RuntimeError(f"Failed to create branch: {err}")
    
    return branch_name
```

---

## Commit Automation

### Commit Message Format

```
{type}({scope}): {short description}

[{issue-ref}] {detailed description of changes}

- {change 1}
- {change 2}

Co-authored-by: openhands <openhands@all-hands.dev>
```

**Types:** feat, fix, docs, test, refactor, perf, security, chore

**Examples:**
```
feat(backend): add rate limiting to auth endpoints

[#22] Implements rate limiting for login and signup endpoints
to prevent brute force attacks.

- Added rate limit middleware (10 req/min per IP)
- Added rate limit headers to responses
- Added tests for rate limit behavior

Co-authored-by: openhands <openhands@all-hands.dev>
```

### Commit Process

```python
def commit_changes(
    files: list[str],
    message: str,
    author_name: str = "openhands",
    author_email: str = "openhands@all-hands.dev"
) -> str:
    """
    Commit changes with proper formatting.
    
    Returns the commit SHA on success.
    """
    # Stage files
    for file in files:
        run_command(["git", "add", file])
    
    # Configure commit author
    run_command([
        "git", "config", "user.name", author_name
    ])
    run_command([
        "git", "config", "user.email", author_email
    ])
    
    # Create commit
    code, output, err = run_command([
        "git", "commit", "-m", message
    ])
    
    if code != 0:
        raise RuntimeError(f"Failed to commit: {err}")
    
    # Get commit SHA
    code, sha, _ = run_command([
        "git", "rev-parse", "HEAD"
    ])
    
    return sha.strip()


def push_branch(branch_name: str, force: bool = False) -> bool:
    """Push branch to remote."""
    cmd = ["git", "push", "-u", "origin", branch_name]
    if force:
        cmd.insert(2, "--force")
    
    code, _, err = run_command(cmd)
    
    if code != 0:
        print(f"Failed to push: {err}")
        return False
    
    return True
```

---

## PR Automation

### PR Template

All PRs must follow this structure:

```markdown
## Summary

{2-3 sentence description of changes}

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement
- [ ] Security fix

## Motivation and Context

Why is this change needed?
- {reason 1}
- {reason 2}

## How Has This Been Tested?

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings or errors

## Evidence

{link to test results, benchmarks, screenshots}

## Related Issue

Fixes #{issue_number}

---

*Generated by OpenClaw GitHub Control Plane*
```

### PR Creation Process

```python
def create_pr(
    owner: str,
    repo: str,
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main",
    labels: list[str] = None,
    reviewers: list[str] = None
) -> dict:
    """
    Create a pull request via GitHub API.
    
    Returns PR info dict on success.
    """
    cmd = [
        "gh", "pr", "create",
        "--repo", f"{owner}/{repo}",
        "--base", base_branch,
        "--head", branch_name,
        "--title", title,
        "--body", body,
    ]
    
    if labels:
        cmd.extend(["--label", ",".join(labels)])
    
    if reviewers:
        cmd.extend(["--reviewer", ",".join(reviewers)])
    
    code, output, err = run_command(cmd)
    
    if code != 0:
        raise RuntimeError(f"Failed to create PR: {err}")
    
    # Parse PR URL from output
    return {"url": output.strip(), "branch": branch_name}


def format_pr_body(
    summary: str,
    motivation: str,
    testing: str,
    issue_number: int,
    changes: list[str] = None,
    labels: list[str] = None,
    evidence: str = None
) -> str:
    """Format a PR body according to the template."""
    
    change_items = ""
    if changes:
        change_items = "\n".join(f"- {c}" for c in changes)
    
    label_items = ""
    if labels:
        for label in labels:
            label_items += f"- [ ] {label}\n"
    
    evidence_section = ""
    if evidence:
        evidence_section = f"\n## Evidence\n\n{evidence}\n"
    
    return f"""## Summary

{summary}

## Motivation and Context

{motivation}

## Changes

{change_items or "- (none)"}

{evidence_section}## How Has This Been Tested?

{testing}

## Checklist

{label_items or "- [ ] (no specific type)"}## Related Issue

Fixes #{issue_number}

---

*Generated by OpenClaw GitHub Control Plane*
"""
```

---

## Safe Implementation Checklist

### Before Any Code Change

- [ ] Issue exists with `openhands` mentioned
- [ ] Issue has `mode:write-approved` label or explicit approval comment
- [ ] Preflight checks all passed
- [ ] Branch naming convention followed
- [ ] Base branch is main (or approved release branch)
- [ ] Working directory is clean

### During Implementation

- [ ] Changes are scoped to the issue
- [ ] Tests added for new functionality
- [ ] No secrets or credentials added
- [ ] No production configuration changes
- [ ] Code follows project style guidelines

### Before PR Creation

- [ ] All preflight checks passed
- [ ] Commit message follows convention
- [ ] PR body follows template
- [ ] Issue is linked with "Fixes #{issue}"
- [ ] Labels added appropriately

### After PR Creation

- [ ] PR URL recorded
- [ ] Original issue updated with PR link
- [ ] Human review requested
- [ ] Monitoring PR status

---

## Rollback Procedures

### If a PR Needs to be Abandoned

```bash
# Close PR
gh pr close {pr-number} --comment "Abandoning this PR as the approach needs revision"

# Delete branch
git checkout main
git branch -D openhands/{issue}-{description}
git push origin --delete openhands/{issue}-{description}
```

### If a Merged PR Needs Reverting

```bash
# Create revert branch
git checkout main
git pull
git checkout -b openhands/revert-{pr-number}

# Revert merge
git revert -m 1 {merge-commit-sha}

# Push and create revert PR
git push -u origin openhands/revert-{pr-number}
gh pr create --title "Revert PR #{pr-number}" --body "Reverts the problematic changes"
```

---

## Related Documents

- [OPENCLAW_GITHUB_CONTROL_PLANE.md](./OPENCLAW_GITHUB_CONTROL_PLANE.md) - Full architecture
- [OPENCLAW_AUDIT_WORKFLOW.md](./OPENCLAW_AUDIT_WORKFLOW.md) - Audit workflow
- [CEO Report Format](./OPENCLAW_GITHUB_CONTROL_PLANE.md#ceo-report-format) - Report template
