"""Unit tests for the jira_management package structure, exports, and entrypoints."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

# Add src directory to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import jira_management
from jira_management import (
    ORDERED_STAGES,
    JiraApiError,
    JiraClient,
    __version__,
    adf_to_text,
    audit_board_compliance,
    build_parser,
    ensure_gitignore_protection,
    find_project_root,
    map_status_to_standard_stage,
    mask_token,
    read_env_file,
    resolve_credentials,
    save_credentials_to_cache,
    text_to_adf,
    validate_issue_transition_order,
)


class TestPackageStructure(unittest.TestCase):
    def test_version_defined(self):
        self.assertTrue(isinstance(__version__, str))
        self.assertEqual(__version__, "1.0.0")

    def test_package_exports(self):
        expected_exports = [
            "__version__",
            "JiraClient",
            "JiraApiError",
            "ORDERED_STAGES",
            "mask_token",
            "find_project_root",
            "ensure_gitignore_protection",
            "resolve_credentials",
            "save_credentials_to_cache",
            "text_to_adf",
            "adf_to_text",
            "audit_board_compliance",
            "validate_issue_transition_order",
            "build_parser",
            "main",
            "SUPPORTED_AGENTS",
            "list_supported_agents",
            "setup_agent_rules",
            "get_mcp_config_dict",
            "McpServer",
            "run_mcp_server",
            "execute_tool",
            "TOOLS_DEFINITIONS",
        ]
        for exp in expected_exports:
            self.assertTrue(hasattr(jira_management, exp), f"Missing export: {exp}")

    def test_cli_parser_builds(self):
        parser = build_parser()
        self.assertEqual(parser.prog, "jira")
        # Check subcommands
        subparsers_action = next(
            a for a in parser._actions if isinstance(a, subprocess.sys.modules["argparse"]._SubParsersAction)
        )
        self.assertIn("auth", subparsers_action.choices)
        self.assertIn("board", subparsers_action.choices)
        self.assertIn("issue", subparsers_action.choices)
        self.assertIn("sprint", subparsers_action.choices)
        self.assertIn("project", subparsers_action.choices)
        self.assertIn("agents", subparsers_action.choices)
        self.assertIn("mcp", subparsers_action.choices)

    def test_module_execution_help(self):
        res = subprocess.run(
            [sys.executable, "-m", "jira_management", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent / "src"),
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Cross-Platform Jira Management CLI", res.stdout)
        self.assertIn("auth", res.stdout)
        self.assertIn("issue", res.stdout)


if __name__ == "__main__":
    unittest.main()
