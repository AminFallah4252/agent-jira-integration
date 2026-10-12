"""Multi-agent configuration, instruction generator, and cross-agent rule templates.

Supports all major autonomous AI agents and IDEs:
- Universal Agents (AGENTS.md standard)
- Anthropic Claude & Claude Code (CLAUDE.md & MCP)
- Cursor IDE (.cursorrules & .cursor/rules/*.mdc & Cursor MCP)
- Windsurf / Codeium (.windsurfrules)
- GitHub Copilot (.github/copilot-instructions.md)
- Cline & Roo Code (.clinerules & MCP)
- Google Antigravity (SKILL.md)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


AGENTS_MD_TEMPLATE = """# Universal Agent Instructions: Jira Management & Agile Protocol

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
"""


CLAUDE_MD_TEMPLATE = """# Claude & Claude Code Instructions: Jira Management

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
"""


CURSOR_RULES_TEMPLATE = """# Cursor AI Rules: Jira Management & Agile Quality Gates

This repository uses the Jira Management CLI/SDK (`jira`). Cursor Composer and Agent must follow these directives:

## 1. Sequential Agile Workflow & DoD Gates
- Progress issues strictly in sequence: `Backlog` -> `To Do` -> `In Progress` -> `In Review` -> `Done`.
- Never transition directly from `To Do` or `Backlog` to `Done`.
- Transitioning to `Done` requires explicit Definition of Done (DoD) verification evidence (test outputs, build results) passed via `--comment` or `--dod-report`.
- Keep Work In Progress (WIP) low: focus on 1 active issue at a time.

## 2. Zero-Leak Credential Safety
- Never hardcode or display API tokens or PATs.
- Credentials auto-resolve from `.agent/jira.json`, `.cursor/jira.json`, `.env`, or environment variables.
- Ensure `.agent/` and `.env*` remain in `.gitignore`.

## 3. Recommended Commands for Cursor Terminal
- Verify authentication: `jira auth status --json`
- View board status: `jira board view`
- Pick up task: `jira issue transition --key <KEY> --to "In Progress"`
- Submit for review: `jira issue transition --key <KEY> --to "In Review"`
- Close with DoD: `jira issue transition --key <KEY> --to "Done" --comment "Verified with tests"`
- Traceability: Cite issue keys in branch names and commit messages (`feat: [#KEY] message`).
"""


CURSOR_MDC_TEMPLATE = """---
description: Enforces Jira Management agile board ordering, sequential issue transitions, and Definition of Done (DoD) gates.
globs: **/*
alwaysApply: true
---

# Jira Management Rules for Cursor

When working on tasks linked to Jira in this project:

1. **Verify Credentials**: Check Jira connectivity using `jira auth status --json`.
2. **Follow 5-Stage Order**:
   - `Backlog` -> `To Do` -> `In Progress` -> `In Review` -> `Done`.
   - Never skip `In Progress` or `In Review`.
3. **Definition of Done (DoD)**:
   - Moving to `Done` is gated. You must run tests and provide proof via:
     `jira issue transition --key <KEY> --to "Done" --comment "Verified: <test results>"`
4. **Zero-Leak**:
   - Never output or log API tokens.
   - Cache lives safely in `.agent/jira.json` or `.cursor/jira.json`.
"""


WINDSURF_RULES_TEMPLATE = """# Windsurf Rules: Jira Management & Agile Protocol

You are operating in a repository integrated with Jira Management (`jira`). Adhere to these instructions:

## Agile Lifecycle & Quality Gates
- Every Jira issue must follow the 5 standard stages in sequential order:
  Stage 1 (Backlog) -> Stage 2 (To Do) -> Stage 3 (In Progress) -> Stage 4 (In Review) -> Stage 5 (Done)
- Never skip intermediate stages.
- Transition to `Done` requires concrete Definition of Done (DoD) evidence (test command output, build verification) attached via `--comment` or `--dod-report`.

## Zero-Leak Secrets
- Do not expose or log tokens.
- Credentials resolve automatically from `.agent/jira.json`, `.env`, or environment variables.

## Key CLI Operations
- Status check: `jira auth status --json`
- Pick up issue: `jira issue transition --key <KEY> --to "In Progress"`
- Request review: `jira issue transition --key <KEY> --to "In Review"`
- Mark done: `jira issue transition --key <KEY> --to "Done" --comment "Verified: tests passed"`
- Log work: `jira issue worklog --key <KEY> --time "2h" --comment "Implemented feature"`
"""


COPILOT_INSTRUCTIONS_TEMPLATE = """# GitHub Copilot Instructions: Jira Management

When assisting developers in this repository:

1. **Agile Workflow & Issue Progression**:
   - Tasks follow the 5 mandatory stages: Backlog -> To Do -> In Progress -> In Review -> Done.
   - Do not recommend skipping stages.
   - Transitioning to Done requires Definition of Done (DoD) test verification.
2. **Traceability**:
   - Format commit messages and branch names with Jira issue keys:
     - Branch: `feature/#<KEY>-<slug>` or `fix/#<KEY>-<slug>`
     - Commit: `feat: [#<KEY>] <message>` or `fix: [#<KEY>] <message>`
3. **Zero-Leak Credential Safety**:
   - Never hardcode or suggest committing API tokens, PATs, or `.env` files.
   - Use the `jira` CLI or SDK which auto-resolves from `.agent/jira.json` or environment variables.
"""


CLINERULES_TEMPLATE = """# Cline & Roo Code Rules: Jira Management

This workspace uses the Jira Management CLI (`jira` / `jira-management`) and MCP server.

## Directives
1. **Zero-Leak Protocol**: Never read, print, or expose raw Jira credentials.
2. **Strict 5-Stage Progression**:
   - Backlog -> To Do -> In Progress -> In Review -> Done.
   - Transitions to `Done` MUST include verification evidence via `--comment` or `--dod-report`.
3. **CLI Commands**:
   - Check connection: `jira auth status --json`
   - Progress issue: `jira issue transition --key <KEY> --to "In Progress"`
   - Ready for review: `jira issue transition --key <KEY> --to "In Review"`
   - Complete issue: `jira issue transition --key <KEY> --to "Done" --comment "Verified: <evidence>"`
"""


SUPPORTED_AGENTS = {
    "universal": {
        "name": "Universal Agent (AGENTS.md)",
        "description": "Standardized instructions for any modern AI coding agent (Devin, Aider, Codex, Antigravity).",
        "files": ["AGENTS.md"],
    },
    "claude": {
        "name": "Anthropic Claude & Claude Code",
        "description": "CLI instructions for Claude Code and Claude Desktop via CLAUDE.md and MCP.",
        "files": ["CLAUDE.md", ".mcp.json"],
    },
    "cursor": {
        "name": "Cursor IDE",
        "description": "Rules for Cursor Composer and Chat via .cursorrules, .cursor/rules, and MCP.",
        "files": [".cursorrules", ".cursor/rules/jira-management.mdc", ".cursor/mcp.json"],
    },
    "windsurf": {
        "name": "Windsurf / Codeium",
        "description": "Instruction set for Windsurf Cascade via .windsurfrules.",
        "files": [".windsurfrules"],
    },
    "copilot": {
        "name": "GitHub Copilot",
        "description": "Repository instructions for GitHub Copilot Workspace and Chat.",
        "files": [".github/copilot-instructions.md"],
    },
    "cline": {
        "name": "Cline & Roo Code",
        "description": "Autonomous developer instructions for Cline and Roo Code via .clinerules.",
        "files": [".clinerules"],
    },
    "antigravity": {
        "name": "Google Antigravity",
        "description": "Official Antigravity skill specification via SKILL.md.",
        "files": ["SKILL.md"],
    },
}


def get_mcp_config_dict(python_cmd: str = "python") -> Dict[str, Any]:
    """Generate universal Model Context Protocol (MCP) server configuration."""
    return {
        "mcpServers": {
            "jira-management": {
                "command": python_cmd,
                "args": ["-m", "jira_management", "mcp"],
                "env": {},
                "disabled": False,
                "autoApprove": [
                    "jira_auth_status",
                    "jira_get_issue",
                    "jira_search_issues",
                    "jira_audit_board",
                    "jira_view_board",
                    "jira_list_projects",
                    "jira_list_sprints",
                ],
            }
        }
    }


def list_supported_agents(project_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List all supported AI agents with their config files and current installation status."""
    root = project_root or Path.cwd()
    results = []

    for agent_id, meta in SUPPORTED_AGENTS.items():
        installed_files = []
        missing_files = []
        for file_rel in meta["files"]:
            target_path = root / file_rel
            if target_path.exists():
                installed_files.append(file_rel)
            else:
                missing_files.append(file_rel)

        results.append({
            "id": agent_id,
            "name": meta["name"],
            "description": meta["description"],
            "all_files": meta["files"],
            "installed_files": installed_files,
            "missing_files": missing_files,
            "status": "fully_installed" if not missing_files else ("partially_installed" if installed_files else "not_installed")
        })

    return results


def setup_agent_rules(
    target_dir: Path,
    agent_names: Optional[List[str]] = None,
    force: bool = False,
    include_mcp: bool = True,
) -> Dict[str, List[Path]]:
    """Generate and write agent rule and instruction files into target_dir."""
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    selected = agent_names or ["all"]
    if "all" in selected:
        agents_to_setup = list(SUPPORTED_AGENTS.keys())
    else:
        agents_to_setup = [a.lower().strip() for a in selected if a.lower().strip() in SUPPORTED_AGENTS]

    created: List[Path] = []
    skipped: List[Path] = []

    def write_file(rel_path: str, content: str) -> None:
        file_path = target_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if file_path.exists() and not force:
            skipped.append(file_path)
            return
        file_path.write_text(content, encoding="utf-8")
        created.append(file_path)

    mcp_json_str = json.dumps(get_mcp_config_dict(), indent=2) + "\n"

    for agent in agents_to_setup:
        if agent == "universal":
            write_file("AGENTS.md", AGENTS_MD_TEMPLATE)
        elif agent == "claude":
            write_file("CLAUDE.md", CLAUDE_MD_TEMPLATE)
            if include_mcp:
                write_file(".mcp.json", mcp_json_str)
        elif agent == "cursor":
            write_file(".cursorrules", CURSOR_RULES_TEMPLATE)
            write_file(".cursor/rules/jira-management.mdc", CURSOR_MDC_TEMPLATE)
            if include_mcp:
                write_file(".cursor/mcp.json", mcp_json_str)
        elif agent == "windsurf":
            write_file(".windsurfrules", WINDSURF_RULES_TEMPLATE)
        elif agent == "copilot":
            write_file(".github/copilot-instructions.md", COPILOT_INSTRUCTIONS_TEMPLATE)
        elif agent == "cline":
            write_file(".clinerules", CLINERULES_TEMPLATE)

    return {"created": created, "skipped": skipped}
