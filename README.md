# Jira Management (Antigravity Skill & Python SDK)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Cross-Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](#)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-green.svg)](#)
[![Zero-Leak Security](https://img.shields.io/badge/Security-Zero--Leak%20Vault-brightgreen.svg)](references/security-and-caching.md)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-orange.svg)](#)
[![Google Antigravity](https://img.shields.io/badge/Skill-Google%20Antigravity-4285F4)](SKILL.md)

An enterprise-grade, cross-platform Python SDK, CLI engine, and Google Antigravity skill for Jira Cloud and Jira Data Center/Server. Built specifically for autonomous AI agents and engineering teams to enforce standardized Agile board workflows, Zero-Leak credential caching, and Definition of Done (DoD) verification gates.

---

## 🌟 Key Highlights

- **Pure Zero-Dependency Standard Library**: Runs anywhere Python 3.8+ is installed with zero `pip install` runtime prerequisites.
- **Modern Package Architecture**: Professional `src/` layout with full typing support (`py.typed`) and PEP 517/621 `pyproject.toml` configuration.
- **Cross-Platform Out-of-the-Box**: Native support for Windows PowerShell (`.\scripts\run.ps1`), Linux/macOS Bash (`./scripts/run.sh`), CLI binary (`jira` / `jira-management`), or direct Python invocation.
- **Zero-Leak Security Ladder**: Auto-protects `.agent/` and `.env` in `.gitignore`, hardens POSIX permissions (`0600`/`0700`), masks secrets in logs, and resolves credentials via a strict priority ladder.
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

### Option 3: Google Antigravity Agent Skill
Copy or link the skill into your Antigravity skills repository:
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

## 🔒 Zero-Leak Credential Resolution Order

Credentials resolve in the following strict descending order:

1. **CLI Flags**: `--url <URL> --token <TOKEN> [--email <EMAIL>]`
2. **Project Cache**: `<project_root>/.agent/jira.json`
3. **Project `.env`**: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` (or `JIRA_PAT`)
4. **Environment Variables**: `os.environ["JIRA_URL"]`, `os.environ["JIRA_API_TOKEN"]`
5. **Global User Cache**: `~/.gemini/config/jira.json`

---

## 📂 Project Architecture

```
agent-jira-integration/
├── .agent/                             # Secure project credentials cache (gitignored)
├── .gitignore                          # Zero-Leak protection for secrets & cache
├── LICENSE                             # MIT License
├── CONTRIBUTING.md                     # Developer contribution guide
├── SKILL.md                            # Antigravity skill specification & instructions
├── README.md                           # Project guide & quickstart
├── pyproject.toml                      # PEP 517/621 packaging configuration
├── src/
│   └── jira_management/               # Python package (src layout)
│       ├── __init__.py                 # Public package API exports & metadata
│       ├── __main__.py                 # Execution entrypoint (python -m jira_management)
│       ├── py.typed                    # PEP 561 typing marker
│       ├── constants.py                # Configuration constants & 5-stage definitions
│       ├── credentials.py              # Zero-Leak credential ladder & caching
│       ├── adf.py                      # Atlassian Document Format (ADF) engine
│       ├── client.py                   # Zero-dependency Jira REST API client
│       ├── workflow.py                 # Enforced board ordering & DoD verification gates
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
