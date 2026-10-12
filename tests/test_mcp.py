#!/usr/bin/env python3
"""
Unit Test Suite for Jira Management Model Context Protocol (MCP) Server
-----------------------------------------------------------------------
Verifies:
- MCP Protocol initialization handshake
- Ping request/response
- Tool list enumeration and schema conformance
- Prompt list and get operations
- Tool execution dispatch and graceful error handling
"""

import json
import unittest
from io import StringIO
from unittest.mock import patch

from jira_management import (
    TOOLS_DEFINITIONS,
    McpServer,
    execute_tool,
)


class TestMcpServer(unittest.TestCase):
    def test_tools_definitions_presence(self):
        tool_names = [t["name"] for t in TOOLS_DEFINITIONS]
        expected = [
            "jira_auth_status",
            "jira_board_audit",
            "jira_board_view",
            "jira_create_issue",
            "jira_get_issue",
            "jira_transition_issue",
            "jira_comment_issue",
            "jira_worklog_issue",
            "jira_search_issues",
            "jira_list_projects",
            "jira_list_sprints",
        ]
        for exp in expected:
            self.assertIn(exp, tool_names)

        # Ensure all tools have inputSchema
        for t in TOOLS_DEFINITIONS:
            self.assertIn("description", t)
            self.assertEqual(t["inputSchema"]["type"], "object")

    def test_execute_tool_auth_status_no_creds(self):
        with patch("jira_management.mcp.resolve_credentials", return_value={"url": None, "token": None}):
            res = execute_tool("jira_auth_status", {})
            self.assertFalse(res["authenticated"])
            self.assertIn("No credentials", res["message"])

    def test_execute_unknown_tool_raises(self):
        with self.assertRaises(ValueError):
            execute_tool("unknown_tool_xyz", {})

    def test_mcp_server_initialize_handshake(self):
        server = McpServer()
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }

        with patch("sys.stdout", new_callable=StringIO) as fake_out:
            server._handle_request(req)
            output = fake_out.getvalue().strip()

        resp = json.loads(output)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "jira-management")
        self.assertIn("tools", resp["result"]["capabilities"])

    def test_mcp_server_ping(self):
        server = McpServer()
        req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}

        with patch("sys.stdout", new_callable=StringIO) as fake_out:
            server._handle_request(req)
            output = fake_out.getvalue().strip()

        resp = json.loads(output)
        self.assertEqual(resp["id"], 2)
        self.assertEqual(resp["result"], {})

    def test_mcp_server_tools_list(self):
        server = McpServer()
        req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}

        with patch("sys.stdout", new_callable=StringIO) as fake_out:
            server._handle_request(req)
            output = fake_out.getvalue().strip()

        resp = json.loads(output)
        self.assertEqual(resp["id"], 3)
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), len(TOOLS_DEFINITIONS))

    def test_mcp_server_prompts_list_and_get(self):
        server = McpServer()
        req_list = {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"}

        with patch("sys.stdout", new_callable=StringIO) as fake_out:
            server._handle_request(req_list)
            output = fake_out.getvalue().strip()

        resp_list = json.loads(output)
        self.assertEqual(resp_list["id"], 4)
        prompts = resp_list["result"]["prompts"]
        self.assertTrue(len(prompts) >= 1)

        req_get = {"jsonrpc": "2.0", "id": 5, "method": "prompts/get", "params": {"name": "jira_agile_lifecycle"}}
        with patch("sys.stdout", new_callable=StringIO) as fake_out:
            server._handle_request(req_get)
            output_get = fake_out.getvalue().strip()

        resp_get = json.loads(output_get)
        self.assertEqual(resp_get["id"], 5)
        self.assertIn("Agile Lifecycle", resp_get["result"]["description"])

    def test_mcp_server_unknown_method(self):
        server = McpServer()
        req = {"jsonrpc": "2.0", "id": 99, "method": "non_existent_method"}

        with patch("sys.stdout", new_callable=StringIO) as fake_out:
            server._handle_request(req)
            output = fake_out.getvalue().strip()

        resp = json.loads(output)
        self.assertEqual(resp["id"], 99)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
