#!/usr/bin/env python3
"""
Unit Test Suite for Multi-Agent Integration & Rule Generators
--------------------------------------------------------------
Verifies:
- Supported agents registry (Claude, Cursor, Windsurf, Copilot, Cline, Antigravity, Universal)
- Agent rule and instruction generation across temporary directories
- Idempotency and --force overwrite handling
- Multi-agent cache paths and .gitignore protection
- MCP config generation for agent configurations
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jira_management import (
    SUPPORTED_AGENTS,
    ensure_gitignore_protection,
    get_all_global_cache_paths,
    get_all_project_cache_paths,
    get_mcp_config_dict,
    list_supported_agents,
    resolve_credentials,
    save_credentials_to_cache,
    setup_agent_rules,
)


class TestAgentsIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="jira_agents_test_"))

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_supported_agents_registry(self):
        self.assertIn("claude", SUPPORTED_AGENTS)
        self.assertIn("cursor", SUPPORTED_AGENTS)
        self.assertIn("windsurf", SUPPORTED_AGENTS)
        self.assertIn("copilot", SUPPORTED_AGENTS)
        self.assertIn("cline", SUPPORTED_AGENTS)
        self.assertIn("universal", SUPPORTED_AGENTS)
        self.assertIn("antigravity", SUPPORTED_AGENTS)

    def test_setup_all_agent_rules(self):
        result = setup_agent_rules(self.test_dir, agent_names=["all"], force=False, include_mcp=True)
        self.assertTrue(len(result["created"]) >= 7)
        self.assertEqual(len(result["skipped"]), 0)

        # Check expected files
        self.assertTrue((self.test_dir / "AGENTS.md").exists())
        self.assertTrue((self.test_dir / "CLAUDE.md").exists())
        self.assertTrue((self.test_dir / ".cursorrules").exists())
        self.assertTrue((self.test_dir / ".cursor" / "rules" / "jira-management.mdc").exists())
        self.assertTrue((self.test_dir / ".cursor" / "mcp.json").exists())
        self.assertTrue((self.test_dir / ".windsurfrules").exists())
        self.assertTrue((self.test_dir / ".github" / "copilot-instructions.md").exists())
        self.assertTrue((self.test_dir / ".clinerules").exists())
        self.assertTrue((self.test_dir / ".mcp.json").exists())

        # Verify idempotency without force
        result_second = setup_agent_rules(self.test_dir, agent_names=["all"], force=False)
        self.assertEqual(len(result_second["created"]), 0)
        self.assertTrue(len(result_second["skipped"]) >= 7)

        # Verify force overwrite
        result_force = setup_agent_rules(self.test_dir, agent_names=["all"], force=True)
        self.assertTrue(len(result_force["created"]) >= 7)

    def test_setup_specific_agent(self):
        result = setup_agent_rules(self.test_dir, agent_names=["claude"], force=False, include_mcp=True)
        self.assertTrue((self.test_dir / "CLAUDE.md").exists())
        self.assertTrue((self.test_dir / ".mcp.json").exists())
        self.assertFalse((self.test_dir / ".cursorrules").exists())

    def test_list_supported_agents_statuses(self):
        agents_before = list_supported_agents(self.test_dir)
        claude_before = next(a for a in agents_before if a["id"] == "claude")
        self.assertEqual(claude_before["status"], "not_installed")

        # Setup claude
        setup_agent_rules(self.test_dir, agent_names=["claude"], include_mcp=True)
        agents_after = list_supported_agents(self.test_dir)
        claude_after = next(a for a in agents_after if a["id"] == "claude")
        self.assertEqual(claude_after["status"], "fully_installed")

    def test_mcp_config_structure(self):
        cfg = get_mcp_config_dict(python_cmd="python3")
        self.assertIn("mcpServers", cfg)
        self.assertIn("jira-management", cfg["mcpServers"])
        server_info = cfg["mcpServers"]["jira-management"]
        self.assertEqual(server_info["command"], "python3")
        self.assertEqual(server_info["args"], ["-m", "jira_management", "mcp"])
        self.assertIn("jira_auth_status", server_info["autoApprove"])

    def test_multi_agent_cache_locations(self):
        project_caches = get_all_project_cache_paths(self.test_dir)
        self.assertEqual(len(project_caches), 3)
        self.assertTrue(any(".claude" in str(p) for p in project_caches))
        self.assertTrue(any(".cursor" in str(p) for p in project_caches))

        global_caches = get_all_global_cache_paths()
        self.assertTrue(len(global_caches) >= 4)
        self.assertTrue(any(".claude" in str(p) for p in global_caches))
        self.assertTrue(any(".cursor" in str(p) for p in global_caches))

    def test_claude_project_cache_resolution(self):
        claude_dir = self.test_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        claude_cache = claude_dir / "jira.json"
        claude_cache.write_text(json.dumps({
            "version": "1.0",
            "profiles": {
                "default": {
                    "url": "https://claude-agent.atlassian.net",
                    "email": "claude@ai.com",
                    "token": "claude_token_123",
                    "project": "CLAUDE",
                    "board_id": 99,
                }
            }
        }), encoding="utf-8")

        creds = resolve_credentials(project_root=self.test_dir)
        self.assertEqual(creds["url"], "https://claude-agent.atlassian.net")
        self.assertEqual(creds["token"], "claude_token_123")
        self.assertEqual(creds["project"], "CLAUDE")
        self.assertIn(".claude", creds["source"])

    def test_gitignore_protects_multi_agent_caches(self):
        ensure_gitignore_protection(self.test_dir)
        gitignore = self.test_dir / ".gitignore"
        self.assertTrue(gitignore.exists())
        content = gitignore.read_text(encoding="utf-8")
        self.assertIn(".agent/", content)
        self.assertIn(".claude/jira.json", content)
        self.assertIn(".cursor/jira.json", content)


if __name__ == "__main__":
    unittest.main()
