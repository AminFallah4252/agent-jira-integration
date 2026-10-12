# GitHub Copilot Instructions: Jira Management

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
