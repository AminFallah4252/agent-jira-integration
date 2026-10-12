#!/usr/bin/env python3
"""
Jira Management CLI & SDK (Scripts Runner & Backwards-Compatibility Shim)
--------------------------------------------------------------------------
Standalone script entry point and backward-compatible shim for the
`jira_management` package.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure 'src' is on sys.path when run directly from repository clone
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Re-export all symbols from jira_management for backwards compatibility
from jira_management import (
    CACHE_DIR_NAME,
    CACHE_FILE_NAME,
    ENV_EMAIL_VAR,
    ENV_PAT_VAR,
    ENV_TOKEN_VAR,
    ENV_URL_VAR,
    ORDERED_STAGES,
    SUPPORTED_AGENTS,
    JiraApiError,
    JiraClient,
    McpServer,
    TOOLS_DEFINITIONS,
    adf_to_text,
    audit_board_compliance,
    build_parser,
    ensure_gitignore_protection,
    execute_tool,
    find_project_root,
    get_all_global_cache_paths,
    get_all_project_cache_paths,
    get_global_cache_path,
    get_mcp_config_dict,
    get_project_cache_path,
    list_supported_agents,
    main,
    map_status_to_standard_stage,
    mask_token,
    read_env_file,
    remove_credentials_from_cache,
    resolve_credentials,
    run_mcp_server,
    save_credentials_to_cache,
    setup_agent_rules,
    text_to_adf,
    validate_issue_transition_order,
)
from jira_management.cli import (
    handle_agents_cmd,
    handle_auth_cmd,
    handle_board_cmd,
    handle_issue_cmd,
    handle_mcp_cmd,
    handle_project_cmd,
    handle_sprint_cmd,
    print_error,
    print_header,
    print_success,
    print_warning,
)

__all__ = [
    "CACHE_DIR_NAME",
    "CACHE_FILE_NAME",
    "ENV_EMAIL_VAR",
    "ENV_PAT_VAR",
    "ENV_TOKEN_VAR",
    "ENV_URL_VAR",
    "ORDERED_STAGES",
    "SUPPORTED_AGENTS",
    "JiraApiError",
    "JiraClient",
    "McpServer",
    "TOOLS_DEFINITIONS",
    "adf_to_text",
    "audit_board_compliance",
    "build_parser",
    "ensure_gitignore_protection",
    "execute_tool",
    "find_project_root",
    "get_all_global_cache_paths",
    "get_all_project_cache_paths",
    "get_global_cache_path",
    "get_mcp_config_dict",
    "get_project_cache_path",
    "handle_agents_cmd",
    "handle_auth_cmd",
    "handle_board_cmd",
    "handle_issue_cmd",
    "handle_mcp_cmd",
    "handle_project_cmd",
    "handle_sprint_cmd",
    "list_supported_agents",
    "main",
    "map_status_to_standard_stage",
    "mask_token",
    "print_error",
    "print_header",
    "print_success",
    "print_warning",
    "read_env_file",
    "remove_credentials_from_cache",
    "resolve_credentials",
    "run_mcp_server",
    "save_credentials_to_cache",
    "setup_agent_rules",
    "text_to_adf",
    "validate_issue_transition_order",
]

if __name__ == "__main__":
    main()
