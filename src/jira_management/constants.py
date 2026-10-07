"""Constants and default configuration for jira-management."""

from __future__ import annotations

__version__ = "1.0.0"

CACHE_DIR_NAME = ".agent"
CACHE_FILE_NAME = "jira.json"
ENV_URL_VAR = "JIRA_URL"
ENV_EMAIL_VAR = "JIRA_EMAIL"
ENV_TOKEN_VAR = "JIRA_API_TOKEN"
ENV_PAT_VAR = "JIRA_PAT"

# Standard Skill Board Workflow Stages & Progression Order
# Every project board managed by this skill must follow this sequential ordering.
ORDERED_STAGES = [
    {
        "order": 1,
        "stage": "Backlog",
        "category": "To Do",
        "description": "Unscheduled backlog items, requirements, raw requests",
        "common_statuses": ["backlog", "open", "submitted", "new", "funnel"]
    },
    {
        "order": 2,
        "stage": "To Do",
        "category": "To Do",
        "description": "Selected for development / active sprint backlog",
        "common_statuses": ["to do", "selected for development", "ready", "planned", "sprint backlog"]
    },
    {
        "order": 3,
        "stage": "In Progress",
        "category": "In Progress",
        "description": "Active development or investigation (WIP limits apply)",
        "common_statuses": ["in progress", "active", "developing", "investigation", "wip"]
    },
    {
        "order": 4,
        "stage": "In Review",
        "category": "In Progress",
        "description": "Ground-truth verification, code review, automated testing, DoD validation",
        "common_statuses": ["in review", "review", "testing", "qa", "verification", "dod check", "qa ready"]
    },
    {
        "order": 5,
        "stage": "Done",
        "category": "Done",
        "description": "Verified complete, DoD satisfied, merged, and closed",
        "common_statuses": ["done", "closed", "resolved", "completed", "verified"]
    }
]
