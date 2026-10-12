# Universal Agent Instructions: Jira Management & Agile Protocol

This repository is integrated with **Jira Management** (`jira` / `jira-management`).
All autonomous AI coding agents (Claude, Cursor, Copilot, Windsurf, Cline, Antigravity, and other LLMs) operating in this workspace must adhere to the following directives.

---

## 🧭 1. Agile Lifecycle & Enforced Board Ordering

Every Jira board and task must strictly progress sequentially through the **5 Mandatory Stages**:

1. **Stage 1 (Backlog)**: Unscheduled items, feature ideas, requirements (`Backlog`, `Open`, `Submitted`, `New`).
2. **Stage 2 (To Do)**: Sprint backlog, planned, ready for development (`To Do`, `Ready`, `Selected for Development`).
3. **Stage 3 (In Progress)**: Active implementation (WIP limit: max 1-2 active tasks per agent).
4. **Stage 4 (In Review / Verification)**: Ground-truth verification, code review, automated testing (`In Review`, `Testing`, `QA`).
5. **Stage 5 (Done)**: Verified complete with DoD proof, PR merged, closed (`Done`, `Closed`, `Resolved`).

### Golden Transition Rules:
- **No Forward Skips**: Never jump directly from `Backlog` or `To Do` straight to `Done`. You must pass through `In Progress` and `In Review`.
- **Definition of Done (DoD) Gate**: Transitioning from `In Review` to `Done` requires verifiable evidence (unit test output, build confirmation, PR review) provided via `--comment` or `--dod-report`.
- **Traceability**: All branch names and commit messages must cite the Jira issue key (e.g. `feat: [#PROJ-123] add auth module`).

---

## 🔐 2. Zero-Leak Credential Ladder

Credentials resolve automatically in descending order:
1. Explicit CLI arguments (`--url`, `--token`, `--email`)
2. Project cache: `.agent/jira.json` (or `.claude/jira.json`, `.cursor/jira.json`)
3. Project `.env` file: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` / `JIRA_PAT`
4. Environment variables: `os.environ["JIRA_URL"]`, `os.environ["JIRA_API_TOKEN"]`
5. Global user caches: `~/.claude/jira.json`, `~/.cursor/jira.json`, `~/.config/jira/jira.json`, `~/.gemini/config/jira.json`

**Security Directives**:
- Never echo, print, or log raw tokens or passwords.
- Always verify that `.agent/`, `.env*`, and credential files are listed in `.gitignore`.

---

## ⚡ 3. Essential CLI Commands

```bash
# Check authentication status (Zero-Leak masked output)
jira auth status
# Output JSON for agent parsing
jira auth status --json

# Audit board compliance against the 5-stage standard
jira board audit --board-id <ID>

# Create issue
jira issue create --summary "Task title" --project <KEY> --type Task --description "Details"

# Transition issue through ordered stages
jira issue transition --key <KEY> --to "In Progress"
jira issue transition --key <KEY> --to "In Review"
jira issue transition --key <KEY> --to "Done" --comment "Verified: 15 unit tests passed, coverage > 90%"

# Add comment / Log time spent
jira issue comment --key <KEY> --body "Implementation finished."
jira issue worklog --key <KEY> --time "2h 30m" --comment "Refactored token refresh."

# Search issues via JQL
jira issue search --jql "project = PROJ AND statusCategory != Done ORDER BY priority DESC"
```
