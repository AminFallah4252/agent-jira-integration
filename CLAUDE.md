# Claude & Claude Code Instructions: Jira Management

You are an expert AI software engineer assisting in this repository. This project uses the **Jira Management** SDK and CLI (`jira` / `jira-management`) to coordinate issue tracking, enforce Definition of Done (DoD) gates, and manage sprints.

---

## 🛡️ Core Operating Rules

1. **Zero-Leak Secret Safety**:
   - Never print, echo, or log full Jira API tokens or Personal Access Tokens (PATs).
   - Verify credentials via `jira auth status --json` before performing mutations.
   - Credentials resolve automatically from `.agent/jira.json`, `.claude/jira.json`, `.env`, or environment variables.

2. **Sequential Agile Lifecycle (DoD Verification Gates)**:
   - All tasks strictly progress in order:
     `Backlog (1)` -> `To Do (2)` -> `In Progress (3)` -> `In Review (4)` -> `Done (5)`
   - Never skip stages (e.g. jumping from `To Do` straight to `Done` is strictly prohibited).
   - When transitioning an issue to `Done`, you **must** provide concrete Definition of Done evidence via `--comment` or `--dod-report` (e.g., test suite results, build output, or commit diff).

3. **Git & Issue Traceability**:
   - Reference the Jira key in commit messages and branch names (e.g., `git checkout -b feature/#PROJ-42-login`, `git commit -m "feat: [#PROJ-42] implement login handler"`).

---

## 💻 CLI Quick Reference for Claude

Run these commands directly in bash or terminal:

```bash
# Check Jira connectivity & profile
jira auth status --json

# Audit board compliance (0-100%)
jira board audit --json

# Create new issue
jira issue create --project <KEY> --summary "<Title>" --type "Task" --description "<Details>"

# Start work (Move to In Progress)
jira issue transition --key <KEY> --to "In Progress"

# Submit for testing (Move to In Review)
jira issue transition --key <KEY> --to "In Review"

# Finalize task (Move to Done with DoD verification proof)
jira issue transition --key <KEY> --to "Done" --comment "Verified: Automated test suite passed, lint checks clean."

# Add comment / log work
jira issue comment --key <KEY> --body "<Progress update>"
jira issue worklog --key <KEY> --time "1h 30m" --comment "<Summary of work>"

# Search issues with JQL
jira issue search --jql "project = <KEY> AND statusCategory != Done"
```

## 🔌 Model Context Protocol (MCP) Mode

If running in Claude Desktop or Claude Code with MCP enabled:
- Use the `jira_*` tools directly (`jira_create_issue`, `jira_get_issue`, `jira_transition_issue`, `jira_audit_board`, etc.).
- Run `jira mcp` to start the local MCP stdio server.
