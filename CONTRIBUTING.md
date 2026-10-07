# Contributing to Jira Management

Thank you for your interest in contributing to `jira-management`!

---

## 🧭 Development Workflow

1. **Fork & Clone** the repository:
   ```bash
   git clone https://github.com/AminFallah4252/agent-jira-integration.git
   cd agent-jira-integration
   ```

2. **Set Up Development Environment**:
   ```bash
   # Install package in editable mode
   python -m pip install -e .
   ```

3. **Running Tests**:
   Zero dependencies are required to run tests:
   ```bash
   # Run with pytest
   pytest

   # Or run with standard unittest
   python -m unittest discover tests
   ```

---

## 🔒 Security & Zero-Leak Protocol

- **Never commit secrets**: All tokens, PATs, or `.env` files must NEVER be staged or committed.
- The `.agent/` folder and `.env*` files are strictly protected in `.gitignore`.
- Always verify before committing:
  ```powershell
  git status --short | Select-String -Pattern "(\.env|token|credentials|key|\.pem)"
  ```

---

## 📝 Commit Guidelines

This project strictly follows [Conventional Commits v1.0.0](https://www.conventionalcommits.org/):

- `feat:` A new feature or capability
- `fix:` A bug fix
- `docs:` Documentation improvements
- `refactor:` Code refactoring without behavioral change
- `test:` Adding or updating tests
- `chore:` Maintenance tasks, dependency bumps
