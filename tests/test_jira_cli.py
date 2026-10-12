#!/usr/bin/env python3
"""
Unit & Integration Test Suite for Jira Management Skill
-------------------------------------------------------
Verifies:
- Token masking and Zero-Leak credential protection
- Project root discovery and automatic .gitignore protection
- Credential resolution ladder (explicit > cache > .env > env vars > global)
- ADF (Atlassian Document Format) serialization & deserialization
- Board workflow audit and compliance scoring against the 5-stage standard
- Sequential transition order validation & Definition of Done (DoD) gates
- Mock Jira API client operations
"""

import http.server
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
import sys

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from jira_cli import (
    ORDERED_STAGES,
    JiraApiError,
    JiraClient,
    adf_to_text,
    audit_board_compliance,
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


class TestSecurityAndResolution(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="jira_test_"))

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_mask_token(self):
        self.assertEqual(mask_token(None), "<no-token>")
        self.assertEqual(mask_token(""), "<no-token>")
        self.assertEqual(mask_token("123"), "***")
        self.assertEqual(mask_token("ATATT3xFfGF01234567890abcdef"), "ATAT***cdef")
        self.assertEqual(mask_token("secret_pat_99"), "secr***t_99")

    def test_ensure_gitignore_protection(self):
        # Empty directory: creates .gitignore with .agent/
        ensure_gitignore_protection(self.test_dir, ".agent/")
        gitignore = self.test_dir / ".gitignore"
        self.assertTrue(gitignore.exists())
        content = gitignore.read_text(encoding="utf-8")
        self.assertIn(".agent/", content)
        self.assertIn(".env", content)

        # Idempotent: does not duplicate
        ensure_gitignore_protection(self.test_dir, ".agent/")
        content_after = gitignore.read_text(encoding="utf-8")
        self.assertEqual(content.count(".agent/"), content_after.count(".agent/"))

    def test_credential_resolution_ladder(self):
        # 1. Project cache
        save_credentials_to_cache(
            url="https://cached.atlassian.net",
            email="cache@test.com",
            token="cached_token_123",
            project="CACHE",
            board_id=42,
            project_root=self.test_dir,
            profile="default"
        )

        creds = resolve_credentials(project_root=self.test_dir)
        self.assertEqual(creds["url"], "https://cached.atlassian.net")
        self.assertEqual(creds["email"], "cache@test.com")
        self.assertEqual(creds["token"], "cached_token_123")
        self.assertEqual(creds["project"], "CACHE")
        self.assertEqual(creds["board_id"], 42)
        self.assertIn("project_cache", creds["source"])

        # 2. Explicit argument overrides cache
        explicit_creds = resolve_credentials(
            project_root=self.test_dir,
            explicit_url="https://override.atlassian.net",
            explicit_token="override_token_456"
        )
        self.assertEqual(explicit_creds["url"], "https://override.atlassian.net")
        self.assertEqual(explicit_creds["token"], "override_token_456")
        self.assertEqual(explicit_creds["source"], "explicit_arguments")

    def test_read_env_file(self):
        env_file = self.test_dir / ".env"
        env_file.write_text("JIRA_URL=https://env.atlassian.net\nJIRA_EMAIL=env@test.com\nJIRA_API_TOKEN=env_tok\n", encoding="utf-8")
        parsed = read_env_file(env_file)
        self.assertEqual(parsed["JIRA_URL"], "https://env.atlassian.net")
        self.assertEqual(parsed["JIRA_EMAIL"], "env@test.com")
        self.assertEqual(parsed["JIRA_API_TOKEN"], "env_tok")


class TestAdfConversion(unittest.TestCase):
    def test_plain_text_to_adf(self):
        text = "This is a plain paragraph."
        adf = text_to_adf(text)
        self.assertEqual(adf["version"], 1)
        self.assertEqual(adf["type"], "doc")
        self.assertEqual(len(adf["content"]), 1)
        self.assertEqual(adf["content"][0]["type"], "paragraph")
        self.assertEqual(adf["content"][0]["content"][0]["text"], text)

        # Roundtrip
        extracted = adf_to_text(adf)
        self.assertIn(text, extracted)

    def test_code_block_adf(self):
        text = "```python\nprint('hello world')\n```"
        adf = text_to_adf(text)
        self.assertEqual(adf["content"][0]["type"], "codeBlock")
        self.assertEqual(adf["content"][0]["attrs"]["language"], "python")
        self.assertEqual(adf["content"][0]["content"][0]["text"], "print('hello world')")

    def test_bullet_list_adf(self):
        text = "- Item 1\n- Item 2\n- Item 3"
        adf = text_to_adf(text)
        self.assertEqual(adf["content"][0]["type"], "bulletList")
        self.assertEqual(len(adf["content"][0]["content"]), 3)


class TestBoardOrderingAndAudit(unittest.TestCase):
    def test_stage_mapping(self):
        s1 = map_status_to_standard_stage("Backlog")
        self.assertIsNotNone(s1)
        self.assertEqual(s1["order"], 1)

        s2 = map_status_to_standard_stage("Selected for Development")
        self.assertIsNotNone(s2)
        self.assertEqual(s2["order"], 2)

        s3 = map_status_to_standard_stage("In Progress")
        self.assertIsNotNone(s3)
        self.assertEqual(s3["order"], 3)

        s4 = map_status_to_standard_stage("In Review")
        self.assertIsNotNone(s4)
        self.assertEqual(s4["order"], 4)

        s5 = map_status_to_standard_stage("Done")
        self.assertIsNotNone(s5)
        self.assertEqual(s5["order"], 5)

    def test_board_audit_compliant(self):
        # A board with all 5 standard columns in order
        config = {
            "id": 10,
            "name": "Project Alpha Kanban",
            "columnConfig": {
                "columns": [
                    {"name": "Backlog", "statuses": [{"name": "Backlog"}]},
                    {"name": "To Do", "statuses": [{"name": "To Do"}]},
                    {"name": "In Progress", "statuses": [{"name": "In Progress"}]},
                    {"name": "In Review", "statuses": [{"name": "In Review"}]},
                    {"name": "Done", "statuses": [{"name": "Done"}]}
                ]
            }
        }
        res = audit_board_compliance(config)
        self.assertTrue(res["compliant"])
        self.assertEqual(res["compliance_score"], "100%")
        self.assertEqual(len(res["missing_stages"]), 0)

    def test_board_audit_non_compliant_missing_review(self):
        # A classic non-compliant board skipping Review
        config = {
            "id": 11,
            "name": "Legacy Board",
            "columnConfig": {
                "columns": [
                    {"name": "To Do", "statuses": [{"name": "To Do"}]},
                    {"name": "In Progress", "statuses": [{"name": "In Progress"}]},
                    {"name": "Done", "statuses": [{"name": "Done"}]}
                ]
            }
        }
        res = audit_board_compliance(config)
        self.assertFalse(res["compliant"])
        self.assertIn("In Review", res["missing_stages"])
        self.assertIn("Backlog", res["missing_stages"])

    def test_transition_ordering_and_dod_gate(self):
        # Rule: Cannot jump directly from To Do (2) to Done (5)
        valid, err = validate_issue_transition_order(
            current_status="To Do",
            target_status="Done",
            has_dod_report=False,
            force=False
        )
        self.assertFalse(valid)
        self.assertIn("Ordered Workflow Violation", err)

        # Rule: Transition to Done requires DoD verification evidence
        valid, err = validate_issue_transition_order(
            current_status="In Review",
            target_status="Done",
            has_dod_report=False,
            force=False
        )
        self.assertFalse(valid)
        self.assertIn("Definition of Done Gate", err)

        # Valid transition from In Review to Done with DoD report
        valid, err = validate_issue_transition_order(
            current_status="In Review",
            target_status="Done",
            has_dod_report=True,
            force=False
        )
        self.assertTrue(valid)
        self.assertIsNone(err)

        # Force flag bypasses restrictions
        valid, err = validate_issue_transition_order(
            current_status="To Do",
            target_status="Done",
            has_dod_report=False,
            force=True
        )
        self.assertTrue(valid)


class MockJiraHttpHandler(http.server.BaseHTTPRequestHandler):
    """Simple mock server responding to Jira API requests."""

    def log_message(self, format, *args):
        pass  # Suppress console logs during tests

    def do_GET(self):
        if self.path.startswith("/rest/api/3/myself") or self.path.startswith("/rest/api/2/myself"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "accountId": "557058:mock-account-1234",
                "displayName": "Jira Test Agent",
                "emailAddress": "agent@example.com",
                "active": True,
                "accountType": "app"
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif "/rest/api/3/issue/PROJ-101" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "key": "PROJ-101",
                "fields": {
                    "summary": "Implement Auth Middleware",
                    "status": {"name": "In Progress"},
                    "issuetype": {"name": "Task"},
                    "priority": {"name": "High"}
                }
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif "/rest/agile/1.0/board" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "values": [
                    {"id": 1, "name": "Main Scrum Board", "type": "scrum"},
                    {"id": 2, "name": "Dev Kanban Board", "type": "kanban"}
                ]
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

        if self.path.startswith("/rest/api/3/issue"):
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {"id": "10001", "key": "PROJ-102", "self": "http://mock/rest/api/3/issue/10001"}
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(200)
            self.end_headers()


class TestMockJiraClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), MockJiraHttpHandler)
        cls.port = cls.server.server_port
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_client_myself_and_boards(self):
        client = JiraClient(
            base_url=f"http://127.0.0.1:{self.port}",
            token="dummy_token_123",
            email="agent@example.com"
        )
        # Test myself
        myself = client.get_myself()
        self.assertEqual(myself["displayName"], "Jira Test Agent")
        self.assertEqual(myself["accountId"], "557058:mock-account-1234")

        # Test get issue
        issue = client.get_issue("PROJ-101")
        self.assertEqual(issue["key"], "PROJ-101")
        self.assertEqual(issue["fields"]["summary"], "Implement Auth Middleware")

        # Test create issue
        new_issue = client.create_issue("PROJ", "Add Rate Limiter", "Task", "Description text")
        self.assertEqual(new_issue["key"], "PROJ-102")

        # Test list boards
        boards = client.list_boards()
        self.assertEqual(len(boards), 2)
        self.assertEqual(boards[0]["name"], "Main Scrum Board")


class TestAgentsCliParser(unittest.TestCase):
    def test_parse_agents_list(self):
        from jira_cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["agents", "list", "--target-dir", "./test_dir", "--json"])
        self.assertEqual(args.command, "agents")
        self.assertEqual(args.agents_action, "list")
        self.assertEqual(args.target_dir, "./test_dir")
        self.assertTrue(args.json)

    def test_parse_agents_setup(self):
        from jira_cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["agents", "setup", "--agent", "cursor", "--force"])
        self.assertEqual(args.command, "agents")
        self.assertEqual(args.agents_action, "setup")
        self.assertEqual(args.agent, "cursor")
        self.assertTrue(args.force)

    def test_parse_agents_mcp_config(self):
        from jira_cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["agents", "mcp-config", "--python-cmd", "python3"])
        self.assertEqual(args.command, "agents")
        self.assertEqual(args.agents_action, "mcp-config")
        self.assertEqual(args.python_cmd, "python3")

    def test_parse_mcp_command(self):
        from jira_cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["mcp"])
        self.assertEqual(args.command, "mcp")


if __name__ == "__main__":
    unittest.main()

