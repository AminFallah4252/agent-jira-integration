# Jira API Reference & Integration Guide

Technical reference for Jira Cloud REST API v3 / Agile 1.0 and Jira Data Center / Server REST API v2.

---

## 🔐 Authentication Protocols

### 1. Jira Cloud (Atlassian Cloud)
- **Base URL**: `https://<organization>.atlassian.net`
- **Method**: HTTP Basic Authentication
- **Credentials**:
  - `Username`: User email (e.g. `agent@company.com`)
  - `Password`: Atlassian API Token generated from [Atlassian Account API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
- **Header**:
  ```http
  Authorization: Basic base64(email:api_token)
  ```

### 2. Jira Server & Data Center (Self-Hosted)
- **Base URL**: `https://jira.internal.company.com`
- **Method**: Personal Access Token (PAT) or Basic Auth
- **Credentials**:
  - Personal Access Token created in Jira profile settings
- **Header**:
  ```http
  Authorization: Bearer <PAT>
  ```

---

## 📄 Atlassian Document Format (ADF)

Jira Cloud REST API v3 uses ADF JSON schema for rich-text fields (`description`, `comment`, `environment`).

### ADF Schema Example
```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {
      "type": "paragraph",
      "content": [
        {
          "type": "text",
          "text": "Task description explaining the technical requirement."
        }
      ]
    },
    {
      "type": "codeBlock",
      "attrs": {"language": "python"},
      "content": [
        {
          "type": "text",
          "text": "def verify_token(token: str) -> bool:\n    return bool(token)"
        }
      ]
    },
    {
      "type": "bulletList",
      "content": [
        {
          "type": "listItem",
          "content": [{
            "type": "paragraph",
            "content": [{"type": "text", "text": "Requirement 1"}]
          }]
        }
      ]
    }
  ]
}
```

> [!NOTE]
> The `jira_cli.py` engine automatically converts plain text and markdown strings to ADF and parses ADF responses back to readable text seamlessly.

---

## 🌐 Core API Endpoints

### User & Verification
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/rest/api/3/myself` | `GET` | Returns authenticated user details (`accountId`, `emailAddress`, `displayName`). |

### Projects
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/rest/api/3/project` | `GET` | List all visible projects. |
| `/rest/api/3/project/{key}` | `GET` | Get detailed metadata for a specific project. |

### Issues
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/rest/api/3/issue` | `POST` | Create a new issue (Task, Story, Bug, Epic, Sub-task). |
| `/rest/api/3/issue/{key}` | `GET` | Fetch issue fields, assignee, status, comments. |
| `/rest/api/3/issue/{key}` | `PUT` | Update issue summary, description, priority, or custom fields. |
| `/rest/api/3/issue/{key}/transitions` | `GET` | Discover available workflow transitions for the issue. |
| `/rest/api/3/issue/{key}/transitions` | `POST` | Transition issue status with optional comment. |
| `/rest/api/3/issue/{key}/comment` | `POST` | Add a comment to an issue. |
| `/rest/api/3/issue/{key}/worklog` | `POST` | Log time spent (e.g. `timeSpent: "2h 30m"`). |
| `/rest/api/3/issueLink` | `POST` | Create links between issues (`Relates`, `Blocks`, `Duplicates`). |
| `/rest/api/3/search` | `POST` | Execute JQL search queries. |

### Agile Boards & Sprints
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/rest/agile/1.0/board` | `GET` | List Scrum and Kanban boards. |
| `/rest/agile/1.0/board/{id}` | `GET` | Retrieve board information. |
| `/rest/agile/1.0/board/{id}/configuration` | `GET` | Inspect columns, statuses, and workflow mapping. |
| `/rest/agile/1.0/board/{id}/issue` | `GET` | List all issues on a board. |
| `/rest/agile/1.0/board/{id}/sprint` | `GET` | List sprints for a Scrum board. |
| `/rest/agile/1.0/sprint` | `POST` | Create a new sprint. |
| `/rest/agile/1.0/sprint/{id}/issue` | `GET` | List issues assigned to a sprint. |

---

## 🔍 JQL (Jira Query Language) Quick Cheat-Sheet

```sql
-- All open issues in project DEV assigned to current user
project = DEV AND assignee = currentUser() AND statusCategory != Done ORDER BY priority DESC

-- Issues currently in the mandatory In Review stage
project = PROJ AND status in ("In Review", "Testing", "QA") ORDER BY updated DESC

-- Sprints currently active
project = PROJ AND sprint in openSprints()

-- Unassigned high priority bugs
project = PROJ AND issuetype = Bug AND priority in (High, Highest) AND assignee is EMPTY
```
