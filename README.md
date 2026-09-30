# Jira Management Skill & Engine for Antigravity

[![Cross-Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](#)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-green.svg)](#)
[![Zero-Leak Security](https://img.shields.io/badge/Security-Zero--Leak%20Vault-brightgreen.svg)](#)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-orange.svg)](#)

An enterprise-grade, cross-platform skill and CLI engine for Jira Cloud and Jira Data Center/Server. Built specifically for autonomous AI agents and development teams to enforce standardized Agile board workflows, Zero-Leak credential caching, and Definition of Done (DoD) verification gates.

---

## 🌟 Key Highlights

- **Pure Zero-Dependency Standard Library**: Runs anywhere Python 3.8+ is installed with zero `pip install` prerequisites.
- **Cross-Platform Out-of-the-Box**: Native support for Windows PowerShell (`.\scripts\run.ps1`), Linux/macOS Bash (`./scripts/run.sh`), and direct Python execution (`python scripts/jira_cli.py`).
- **Zero-Leak Security Ladder**: Auto-protects `.agent/` and `.env` in `.gitignore`, hardens POSIX permissions (`0600`/`0700`), masks secrets in logs, and resolves credentials via a strict priority ladder.
- **Enforced Agile Board Order**: Guarantees that every project board adheres to the 5 mandatory stages:
  $$\text{Backlog (1)} \rightarrow \text{To Do (2)} \rightarrow \text{In Progress (3)} \rightarrow \text{In Review (4)} \rightarrow \text{Done (5)}$$
- **Definition of Done (DoD) Gates**: Prohibits skipping stages and blocks transitions to `Done` unless concrete verification evidence or test logs are attached.
- **Dual Output Modes**: Formatted terminal output for humans and clean `--json` output for automated subagents.

---

## 🚀 Quick Start

### 1. Authenticate & Configure Project
```bash
# For Jira Cloud (Atlassian)
python scripts/jira_cli.py auth set \
  --url "https://your-domain.atlassian.net" \
  --email "bot@your-domain.com" \
  --token "ATATT3xFfGF0exampletoken123" \
  --project "PROJ" \
  --board-id 14

# For Jira Data Center / Server (PAT)
python scripts/jira_cli.py auth set \
  --url "https://jira.internal.company.com" \
  --token "your_personal_access_token" \
  --project "CORE"
```

### 2. Verify Authentication
```bash
python scripts/jira_cli.py auth status
```

### 3. Audit Project Board
```bash
python scripts/jira_cli.py board audit --board-id 14
```

### 4. Track Issues Through the Ordered Lifecycle
```bash
# 1. Create issue
python scripts/jira_cli.py issue create --project PROJ --summary "Add JWT Middleware"

# 2. Pick up work: To Do -> In Progress
python scripts/jira_cli.py issue transition --key PROJ-101 --to "In Progress"

# 3. Ready for testing: In Progress -> In Review
python scripts/jira_cli.py issue transition --key PROJ-101 --to "In Review"

# 4. Verified & closed: In Review -> Done (requires DoD proof)
python scripts/jira_cli.py issue transition --key PROJ-101 --to "Done" \
  --comment "Verified: 12 tests passed, lint clean, branch merged."
```

---

## 📂 Project Architecture

```
agent-jira-integration/
├── .agent/                             # Secure project credentials cache (gitignored)
├── .gitignore                          # Zero-Leak protection for secrets & cache
├── SKILL.md                            # Antigravity skill specification & instructions
├── README.md                           # Project guide & quickstart
├── pyproject.toml                      # Standard packaging configuration
├── scripts/
│   ├── jira_cli.py                     # Zero-dependency, cross-platform CLI & Python SDK
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
    └── test_jira_cli.py                # Automated unit & integration tests
```

---

## 🧪 Running Tests

Execute the comprehensive automated test suite (Zero dependencies required):

```bash
python tests/test_jira_cli.py
```
