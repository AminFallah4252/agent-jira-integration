# Jira Management (Universal AI Agent Skill, MCP & Python SDK)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Cross-Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](#)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-green.svg)](#)
[![Multi-Agent Ready](https://img.shields.io/badge/AI%20Agents-Claude%20%7C%20Cursor%20%7C%20Copilot%20%7C%20Windsurf%20%7C%20Cline%20%7C%20Antigravity-purple.svg)](#-universal-multi-agent-support)
[![MCP Protocol](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(MCP)-orange.svg)](#-model-context-protocol-mcp-server)
[![Zero-Leak Security](https://img.shields.io/badge/Security-Zero--Leak%20Vault-brightgreen.svg)](references/security-and-caching.md)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-orange.svg)](#)

An enterprise-grade, cross-platform Python SDK, CLI engine, Model Context Protocol (MCP) server, and universal AI agent skill for Jira Cloud and Jira Data Center/Server. Built specifically for **all autonomous AI coding agents** (Claude, Cursor, GitHub Copilot, Windsurf, Cline, Roo Code, Google Antigravity, and universal LLMs) to enforce standardized Agile board workflows, Zero-Leak credential caching, and Definition of Done (DoD) verification gates.

---

## 🌟 Key Highlights

- **Universal Multi-Agent Support**: Out-of-the-box rule sets and instructions for **Anthropic Claude & Claude Code**, **Cursor IDE**, **Windsurf**, **GitHub Copilot**, **Cline & Roo Code**, **Google Antigravity**, and **Universal Agents (`AGENTS.md`)**.
- **Native Model Context Protocol (MCP) Server**: Zero-dependency stdio JSON-RPC 2.0 server (`jira mcp`) empowering Claude, Cursor, and any MCP client to call Jira tools directly.
- **Automated Agent Setup Engine**: One-click generation of agent instruction files and MCP configs via `jira agents setup` and `jira agents mcp-config`.
- **Pure Zero-Dependency Standard Library**: Runs anywhere Python 3.8+ is installed with zero `pip install` runtime prerequisites.
- **Modern Package Architecture**: Professional `src/` layout with full typing support (`py.typed`) and PEP 517/621 `pyproject.toml` configuration.
- **Cross-Platform Out-of-the-Box**: Native support for Windows PowerShell (`.\scripts\run.ps1`), Linux/macOS Bash (`./scripts/run.sh`), CLI binary (`jira` / `jira-management`), or direct Python invocation.
- **Zero-Leak Security Ladder**: Auto-protects `.agent/`, `.claude/jira.json`, `.cursor/jira.json`, and `.env` in `.gitignore`, hardens POSIX permissions (`0600`/`0700`), masks secrets in logs, and resolves credentials via a strict priority ladder.
- **Enforced Agile Board Order**: Guarantees that every project board adheres to the 5 mandatory stages:
  $$\text{Backlog (1)} \rightarrow \text{To Do (2)} \rightarrow \text{In Progress (3)} \rightarrow \text{In Review (4)} \rightarrow \text{Done (5)}$$
- **Definition of Done (DoD) Gates**: Prohibits skipping stages and blocks transitions to `Done` unless concrete verification evidence or test logs are attached.
- **Dual Output Modes**: Formatted terminal output for humans and clean `--json` output for automated subagents.

---

## 📦 Installation & Setup

### Option 1: Install via pip
```bash
# Install from local clone
pip install .

# Or install in editable mode for development
pip install -e .
```
Once installed, the `jira` and `jira-management` CLI commands are available globally in your environment.

### Option 2: Standalone Execution (No Install Required)
You can directly run the zero-dependency scripts from the repository clone:
```bash
# Windows PowerShell
.\scripts\run.ps1 auth status

# Linux / macOS Bash
./scripts/run.sh auth status

# Direct Python
python scripts/jira_cli.py auth status
```

### Option 3: Equip Any AI Agent (One-Click Setup)
Automatically generate instruction files (`CLAUDE.md`, `.cursorrules`, `.windsurfrules`, `.github/copilot-instructions.md`, `.clinerules`, `AGENTS.md`) and MCP configs for your workspace:

```bash
# Setup all supported agents at once:
jira agents setup

# Or setup a specific agent:
jira agents setup --agent claude
jira agents setup --agent cursor
jira agents setup --agent windsurf
jira agents setup --agent copilot
jira agents setup --agent cline

# Check integration status for all agents:
jira agents list
```

For **Google Antigravity**:
```bash
# Global Antigravity skills directory
cp -r . ~/.gemini/config/skills/jira-management/

# Or per-project skills directory
mkdir -p .agents/skills/
cp -r . .agents/skills/jira-management/
```

---

## 🚀 Quick Start

### 1. Authenticate & Configure Project
```bash
# For Jira Cloud (Atlassian)
jira auth set \
  --url "https://your-domain.atlassian.net" \
  --email "bot@your-domain.com" \
  --token "ATATT3xFfGF0exampletoken123" \
  --project "PROJ" \
  --board-id 14

# For Jira Data Center / Server (PAT)
jira auth set \
  --url "https://jira.internal.company.com" \
  --token "your_personal_access_token" \
  --project "CORE"
```

### 2. Verify Authentication
```bash
jira auth status
```

### 3. Audit Project Board
```bash
jira board audit --board-id 14
```

### 4. Track Issues Through the Ordered Lifecycle
```bash
# 1. Create issue
jira issue create --project PROJ --summary "Add JWT Middleware"

# 2. Pick up work: To Do -> In Progress
jira issue transition --key PROJ-101 --to "In Progress"

# 3. Ready for testing: In Progress -> In Review
jira issue transition --key PROJ-101 --to "In Review"

# 4. Verified & closed: In Review -> Done (requires DoD proof)
jira issue transition --key PROJ-101 --to "Done" \
  --comment "Verified: 12 tests passed, lint clean, branch merged."
```

---

## 🐍 Python SDK Usage

You can import and use `jira_management` directly in your Python codebases:

```python
from jira_management import JiraClient, resolve_credentials, audit_board_compliance

# 1. Automatically resolve credentials via Zero-Leak priority ladder
creds = resolve_credentials()
client = JiraClient(
    base_url=creds["url"],
    token=creds["token"],
    email=creds.get("email"),
)

# 2. Verify connection
user = client.get_myself()
print(f"Logged in as: {user['displayName']}")

# 3. Create an issue with ADF formatting
new_issue = client.create_issue(
    project_key="PROJ",
    summary="Implement API rate limiting",
    issue_type="Task",
    description="Protect endpoints from DDoS using Redis token bucket.",
)
print(f"Created: {new_issue['key']}")

# 4. Audit board compliance
config = client.get_board_configuration(board_id=14)
report = audit_board_compliance(config)
print(f"Board Compliance: {report['compliance_score']} (Compliant: {report['compliant']})")
```

---

## 🤖 Universal Multi-Agent Support

This skill includes pre-configured rule sets and instruction files tailored specifically to each AI coding assistant's runtime requirements:

| Agent / Environment | Rule File(s) Generated | How It Works |
| :--- | :--- | :--- |
| **Anthropic Claude & Claude Code** | `CLAUDE.md`, `.mcp.json` | Claude Code automatically reads `CLAUDE.md` on startup; MCP bindings allow direct tool calling. |
| **Cursor IDE** | `.cursorrules`, `.cursor/rules/jira-management.mdc`, `.cursor/mcp.json` | Loaded by Cursor Composer and Chat to enforce Definition of Done and 5-stage workflows. |
| **Windsurf / Codeium** | `.windsurfrules` | Guides Windsurf Cascade AI with sequential Jira lifecycle gates and Zero-Leak security. |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Injected into GitHub Copilot Workspace and inline chat for prompt and code traceability. |
| **Cline & Roo Code** | `.clinerules` | Enforces autonomous task flow, branch naming, and DoD gates for Cline/Roo Code. |
| **Google Antigravity** | `SKILL.md` | Native skill specification with YAML frontmatter and subagent contracts. |
| **Universal Agents** | `AGENTS.md` | Emerging open multi-agent standard recognized by Devin, Aider, Codex, and other LLMs. |

### CLI Multi-Agent Management:
```bash
# Check integration status for all agents:
jira agents list

# Generate instruction files in current workspace:
jira agents setup

# Setup rules for a specific agent:
jira agents setup --agent claude
jira agents setup --agent cursor

# Export MCP configuration JSON:
jira agents mcp-config

# Automatically write MCP files (.cursor/mcp.json & .mcp.json):
jira agents mcp-config --write
```

---

## 🔌 Model Context Protocol (MCP) Server

Connect Jira Management directly to **Claude Desktop**, **Claude Code**, **Cursor**, **Windsurf**, or **Cline** using the native zero-dependency MCP server.

### 1. Launch the Server Directly
```bash
# Via installed CLI
jira mcp

# Or via Python module
python -m jira_management mcp
```

### 2. Configure in Cursor (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "jira-management": {
      "command": "python",
      "args": ["-m", "jira_management", "mcp"]
    }
  }
}
```

### 3. Configure in Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "jira-management": {
      "command": "python",
      "args": ["-m", "jira_management", "mcp"]
    }
  }
}
```

### Available MCP Tools:
- `jira_auth_status`: Connection check and Zero-Leak profile inspection.
- `jira_create_issue`: Create task, bug, or story with description and labels.
- `jira_get_issue`: Detailed issue view with current stage and status.
- `jira_transition_issue`: Sequential 5-stage transitions enforcing DoD gates.
- `jira_comment_issue`: Add progress comments to issues.
- `jira_worklog_issue`: Log time spent with descriptions.
- `jira_search_issues`: Search issues using JQL queries.
- `jira_audit_board`: Audit Agile boards against the 5-stage standard.
- `jira_view_board`: Stage-by-stage grouped board overview.
- `jira_list_projects`: List all accessible Jira projects.
- `jira_list_sprints`: List sprints on a Scrum board.

---

## 🔒 Zero-Leak Credential Resolution Order

Credentials resolve automatically in the following descending order:

1. **CLI Flags**: `--url <URL> --token <TOKEN> [--email <EMAIL>]`
2. **Multi-Agent Project Caches**:
   - `<project_root>/.agent/jira.json`
   - `<project_root>/.claude/jira.json`
   - `<project_root>/.cursor/jira.json`
3. **Project `.env`**: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` (or `JIRA_PAT`)
4. **Environment Variables**: `os.environ["JIRA_URL"]`, `os.environ["JIRA_API_TOKEN"]`
5. **Global Multi-Agent User Caches**:
   - `~/.gemini/config/jira.json` (Google Antigravity)
   - `~/.claude/jira.json` (Anthropic Claude)
   - `~/.cursor/jira.json` (Cursor IDE)
   - `~/.config/jira/jira.json` (Linux / XDG Standard)
   - `~/.jira/jira.json` or `~/.jira/config.json`

---

## 📂 Project Architecture

```
agent-jira-integration/
├── .agent/                             # Secure project credentials cache (gitignored)
├── .cursor/
│   ├── rules/jira-management.mdc       # Cursor Rules v2 (MDC format)
│   └── mcp.json                        # Cursor MCP server configuration
├── .github/
│   └── copilot-instructions.md         # GitHub Copilot instructions
├── .cursorrules                        # Cursor IDE classic rules
├── .windsurfrules                       # Windsurf / Codeium Cascade rules
├── .clinerules                         # Cline & Roo Code rules
├── .mcp.json                           # Universal / Claude Code MCP configuration
├── AGENTS.md                           # Universal Agent standard instructions
├── CLAUDE.md                           # Anthropic Claude & Claude Code instructions
├── SKILL.md                            # Antigravity skill specification & instructions
├── README.md                           # Project guide & quickstart
├── pyproject.toml                      # PEP 517/621 packaging configuration
├── src/
│   └── jira_management/               # Python package (src layout)
│       ├── __init__.py                 # Public package API exports & metadata
│       ├── __main__.py                 # Execution entrypoint (python -m jira_management)
│       ├── py.typed                    # PEP 561 typing marker
│       ├── constants.py                # Configuration constants & 5-stage definitions
│       ├── credentials.py              # Zero-Leak multi-agent credential ladder
│       ├── adf.py                      # Atlassian Document Format (ADF) engine
│       ├── client.py                   # Zero-dependency Jira REST API client
│       ├── workflow.py                 # Enforced board ordering & DoD verification gates
│       ├── agents.py                   # Multi-agent rule templates & setup engine
│       ├── mcp.py                      # Model Context Protocol (MCP) stdio server
│       └── cli.py                      # Command-line interface & argument parsing
├── scripts/
│   ├── jira_cli.py                     # Zero-dependency standalone CLI runner & shim
│   ├── run.ps1                         # PowerShell entrypoint (Windows)
│   └── run.sh                          # Bash entrypoint (Linux / macOS)
├── references/
│   ├── board-workflow-standard.md      # The 5-stage ordered board methodology
│   ├── jira-api-reference.md           # Cloud v3 & Server v2 REST endpoints & ADF
│   └── security-and-caching.md         # Zero-Leak credential ladder & POSIX ACLs
├── examples/
│   ├── board_onboarding_and_audit.py   # Programmatic board auditing
│   ├── workflow_transition_gate.py     # Sequential transitions & DoD gates
│   └── sprint_burndown_reporter.py     # Stage-by-stage sprint reporting
└── tests/
    ├── test_agents.py                  # Multi-agent rules & setup engine tests
    ├── test_mcp.py                     # Model Context Protocol (MCP) server tests
    ├── test_jira_cli.py                # Standalone script & security integration tests
    └── test_package.py                 # Package layout, exports, and CLI entrypoint tests
```

---

## 🧪 Running Tests

Execute the comprehensive automated test suite (Zero dependencies required):

```bash
# Using pytest
pytest

# Or using Python's standard unittest
python -m unittest discover tests
```

---

## 📄 License

Distributed under the [MIT License](LICENSE). Built by [Amin Fallah](https://github.com/AminFallah4252).
