"""Jira Management Package
-----------------------
Enterprise cross-platform Jira management skill and SDK for autonomous AI agents.
Provides Zero-Leak security, enforced board ordering, Definition of Done gates,
and full Atlassian Cloud / Data Center REST API coverage.
"""

from __future__ import annotations

from .adf import adf_to_text, text_to_adf
from .cli import build_parser, main
from .client import JiraApiError, JiraClient
from .constants import (
    CACHE_DIR_NAME,
    CACHE_FILE_NAME,
    ENV_EMAIL_VAR,
    ENV_PAT_VAR,
    ENV_TOKEN_VAR,
    ENV_URL_VAR,
    ORDERED_STAGES,
    __version__,
)
from .credentials import (
    ensure_gitignore_protection,
    find_project_root,
    get_global_cache_path,
    get_project_cache_path,
    mask_token,
    read_env_file,
    remove_credentials_from_cache,
    resolve_credentials,
    save_credentials_to_cache,
)
from .workflow import (
    audit_board_compliance,
    map_status_to_standard_stage,
    validate_issue_transition_order,
)

__all__ = [
    "__version__",
    "CACHE_DIR_NAME",
    "CACHE_FILE_NAME",
    "ENV_URL_VAR",
    "ENV_EMAIL_VAR",
    "ENV_TOKEN_VAR",
    "ENV_PAT_VAR",
    "ORDERED_STAGES",
    "mask_token",
    "find_project_root",
    "ensure_gitignore_protection",
    "get_project_cache_path",
    "get_global_cache_path",
    "read_env_file",
    "resolve_credentials",
    "save_credentials_to_cache",
    "remove_credentials_from_cache",
    "text_to_adf",
    "adf_to_text",
    "JiraApiError",
    "JiraClient",
    "map_status_to_standard_stage",
    "audit_board_compliance",
    "validate_issue_transition_order",
    "build_parser",
    "main",
]
