"""Zero-dependency Model Context Protocol (MCP) server for Jira Management.

Compatible with Claude Desktop, Claude Code, Cursor, Windsurf, Cline, and any
MCP-compliant AI agent or client.
Communicates via JSON-RPC 2.0 over standard I/O (stdio).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, List, Optional

from .client import JiraApiError, JiraClient
from .credentials import mask_token, resolve_credentials
from .workflow import (
    audit_board_compliance,
    map_status_to_standard_stage,
    validate_issue_transition_order,
)


TOOLS_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "jira_auth_status",
        "description": "Check Jira connectivity, user profile, and active workspace configuration (Zero-Leak token masked).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {"type": "string", "description": "Profile name (default: 'default')"}
            },
        },
    },
    {
        "name": "jira_board_audit",
        "description": "Audit an agile board against the mandatory 5-stage sequential standard (Backlog -> To Do -> In Progress -> In Review -> Done) and compute compliance score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "Jira Agile Board ID"}
            },
        },
    },
    {
        "name": "jira_board_view",
        "description": "Retrieve board issues organized into the 5 standard agile workflow stages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "Jira Agile Board ID"}
            },
        },
    },
    {
        "name": "jira_create_issue",
        "description": "Create a new Jira issue with summary, description, type, priority, and labels.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Issue summary/title"},
                "description": {"type": "string", "description": "Issue description text or markdown"},
                "type": {"type": "string", "description": "Issue type (Task, Bug, Story, Epic)", "default": "Task"},
                "project": {"type": "string", "description": "Project key (or default from cache)"},
                "priority": {"type": "string", "description": "Priority (Lowest, Low, Medium, High, Highest)"},
                "labels": {"type": "string", "description": "Comma-separated labels"},
                "parent": {"type": "string", "description": "Parent issue key for subtasks"},
            },
            "required": ["summary"],
        },
    },
    {
        "name": "jira_get_issue",
        "description": "Get detailed information for a Jira issue including current status, stage, description, and assignee.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Issue key (e.g. PROJ-101)"}
            },
            "required": ["key"],
        },
    },
    {
        "name": "jira_transition_issue",
        "description": "Transition issue status while enforcing the 5-stage sequential order and Definition of Done (DoD) verification gate before reaching Done.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Issue key (e.g. PROJ-101)"},
                "to": {"type": "string", "description": "Target status name (e.g. 'In Progress', 'In Review', 'Done')"},
                "comment": {"type": "string", "description": "Transition comment or DoD explanation"},
                "dod_report": {"type": "string", "description": "Test results, DoD evidence or path to log file"},
                "force": {"type": "boolean", "description": "Bypass sequential transition checks", "default": False},
            },
            "required": ["key", "to"],
        },
    },
    {
        "name": "jira_comment_issue",
        "description": "Add a comment to a Jira issue.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Issue key (e.g. PROJ-101)"},
                "body": {"type": "string", "description": "Comment body text or markdown"},
            },
            "required": ["key", "body"],
        },
    },
    {
        "name": "jira_worklog_issue",
        "description": "Log time spent on a Jira issue.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Issue key (e.g. PROJ-101)"},
                "time": {"type": "string", "description": "Time spent string (e.g. '1h 30m', '45m')"},
                "comment": {"type": "string", "description": "Description of work done"},
            },
            "required": ["key", "time"],
        },
    },
    {
        "name": "jira_search_issues",
        "description": "Search Jira issues using JQL (Jira Query Language).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "JQL query string"},
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
        },
    },
    {
        "name": "jira_list_projects",
        "description": "List all accessible Jira projects in the connected workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "jira_list_sprints",
        "description": "List sprints for an agile Scrum board.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "Board ID"},
                "state": {"type": "string", "description": "Sprint state ('active', 'future', 'closed')"},
            },
            "required": ["board_id"],
        },
    },
]


def _get_client_and_creds(profile: str = "default") -> tuple[JiraClient, Dict[str, Any]]:
    creds = resolve_credentials(profile=profile)
    if not creds.get("url") or not creds.get("token"):
        raise ValueError(
            "Jira credentials not found. Run 'jira auth set' or provide JIRA_URL and JIRA_API_TOKEN."
        )
    client = JiraClient(
        base_url=creds["url"],
        token=creds["token"],
        email=creds.get("email"),
    )
    return client, creds


def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Dispatch and execute an MCP tool call."""
    profile = arguments.get("profile", "default")

    if name == "jira_auth_status":
        creds = resolve_credentials(profile=profile)
        if not creds.get("url") or not creds.get("token"):
            return {
                "authenticated": False,
                "message": "No credentials configured.",
                "source": creds.get("source", "none"),
            }
        client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))
        user = client.get_myself()
        return {
            "authenticated": True,
            "url": creds["url"],
            "masked_token": mask_token(creds.get("token")),
            "source": creds.get("source"),
            "default_project": creds.get("project"),
            "default_board_id": creds.get("board_id"),
            "user": {
                "display_name": user.get("displayName"),
                "email": user.get("emailAddress"),
                "account_id": user.get("accountId"),
            },
        }

    client, creds = _get_client_and_creds(profile=profile)

    if name == "jira_board_audit":
        board_id = arguments.get("board_id") or creds.get("board_id")
        if not board_id:
            raise ValueError("Board ID required.")
        config = client.get_board_configuration(int(board_id))
        return audit_board_compliance(config)

    elif name == "jira_board_view":
        board_id = arguments.get("board_id") or creds.get("board_id")
        if not board_id:
            raise ValueError("Board ID required.")
        issues_res = client.get_board_issues(int(board_id), max_results=100)
        issues = issues_res.get("issues", [])
        grouped: Dict[str, List[Any]] = {
            "Stage 1: Backlog": [],
            "Stage 2: To Do": [],
            "Stage 3: In Progress": [],
            "Stage 4: In Review": [],
            "Stage 5: Done": [],
            "Unmapped": [],
        }
        for iss in issues:
            st_name = iss.get("fields", {}).get("status", {}).get("name", "Unknown")
            stage_info = map_status_to_standard_stage(st_name)
            entry = {
                "key": iss.get("key"),
                "summary": iss.get("fields", {}).get("summary"),
                "status": st_name,
                "assignee": (iss.get("fields", {}).get("assignee") or {}).get("displayName"),
            }
            if stage_info:
                key_name = f"Stage {stage_info['order']}: {stage_info['stage']}"
                grouped[key_name].append(entry)
            else:
                grouped["Unmapped"].append(entry)
        return {"board_id": int(board_id), "grouped_issues": grouped}

    elif name == "jira_create_issue":
        project_key = arguments.get("project") or creds.get("project")
        if not project_key:
            raise ValueError("Project key is required.")
        labels = [l.strip() for l in arguments.get("labels", "").split(",") if l.strip()]
        return client.create_issue(
            project_key=project_key,
            summary=arguments["summary"],
            issue_type=arguments.get("type", "Task"),
            description=arguments.get("description"),
            priority=arguments.get("priority"),
            labels=labels if labels else None,
            parent_key=arguments.get("parent"),
        )

    elif name == "jira_get_issue":
        key = arguments["key"].strip().upper()
        raw = client.get_issue(key)
        fields = raw.get("fields", {})
        status_name = fields.get("status", {}).get("name", "Unknown")
        stage_info = map_status_to_standard_stage(status_name)
        return {
            "key": raw.get("key"),
            "summary": fields.get("summary"),
            "status": status_name,
            "stage": stage_info,
            "issue_type": fields.get("issuetype", {}).get("name"),
            "priority": (fields.get("priority") or {}).get("name"),
            "assignee": (fields.get("assignee") or {}).get("displayName"),
            "labels": fields.get("labels", []),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
        }

    elif name == "jira_transition_issue":
        key = arguments["key"].strip().upper()
        target_to = arguments["to"].strip()
        comment = arguments.get("comment")
        dod_report = arguments.get("dod_report")
        force = bool(arguments.get("force", False))

        issue_data = client.get_issue(key)
        current_status = issue_data.get("fields", {}).get("status", {}).get("name", "Unknown")

        if not force:
            valid, reason = validate_issue_transition_order(
                current_status_name=current_status,
                target_status_name=target_to,
                comment=comment,
                dod_report=dod_report,
            )
            if not valid:
                raise ValueError(f"Transition rejected by Definition of Done (DoD) gate: {reason}")

        transitions_data = client.get_transitions(key)
        available = transitions_data.get("transitions", [])
        matched = None
        for t in available:
            t_name = t.get("name", "").lower()
            to_name = t.get("to", {}).get("name", "").lower()
            if target_to.lower() in (t_name, to_name):
                matched = t
                break

        if not matched:
            avail_names = [f"'{t.get('name')}' -> '{t.get('to', {}).get('name')}'" for t in available]
            raise ValueError(
                f"Transition '{target_to}' not found for {key}. Available: {', '.join(avail_names)}"
            )

        comment_body = comment or (f"DoD Evidence: {dod_report}" if dod_report else None)
        client.transition_issue(key, transition_id=matched["id"], comment=comment_body)
        return {
            "success": True,
            "key": key,
            "previous_status": current_status,
            "new_status": matched.get("to", {}).get("name", target_to),
            "transition_used": matched.get("name"),
            "comment": comment_body,
        }

    elif name == "jira_comment_issue":
        key = arguments["key"].strip().upper()
        body = arguments["body"]
        return client.add_comment(key, body)

    elif name == "jira_worklog_issue":
        key = arguments["key"].strip().upper()
        time_spent = arguments["time"]
        comment = arguments.get("comment")
        return client.add_worklog(key, time_spent=time_spent, comment=comment)

    elif name == "jira_search_issues":
        project_key = creds.get("project")
        jql = arguments.get("jql")
        if not jql:
            if project_key:
                jql = f"project = {project_key} ORDER BY updated DESC"
            else:
                jql = "ORDER BY updated DESC"
        limit = int(arguments.get("limit", 20))
        res = client.search_issues(jql=jql, max_results=limit)
        results = []
        for iss in res.get("issues", []):
            st = iss.get("fields", {}).get("status", {}).get("name", "Unknown")
            results.append({
                "key": iss.get("key"),
                "summary": iss.get("fields", {}).get("summary"),
                "status": st,
                "stage": map_status_to_standard_stage(st),
                "type": iss.get("fields", {}).get("issuetype", {}).get("name"),
                "priority": (iss.get("fields", {}).get("priority") or {}).get("name"),
            })
        return {"total": res.get("total", len(results)), "issues": results}

    elif name == "jira_list_projects":
        return client.get_projects()

    elif name == "jira_list_sprints":
        board_id = int(arguments["board_id"])
        state = arguments.get("state")
        return client.get_board_sprints(board_id=board_id, state=state)

    else:
        raise ValueError(f"Unknown tool: '{name}'")


class McpServer:
    """Lightweight stdio JSON-RPC 2.0 MCP Server."""

    def __init__(self) -> None:
        self.running = True

    def run_stdio(self) -> None:
        """Process requests from stdin and write JSON-RPC responses to stdout."""
        # Ensure UTF-8 I/O
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue

            # Strip HTTP-like Content-Length headers if present
            if line_str.startswith("Content-Length:"):
                continue

            try:
                request = json.loads(line_str)
            except json.JSONDecodeError as err:
                self._send_error(None, -32700, f"Parse error: {err}")
                continue

            self._handle_request(request)

    def _send_response(self, response: Dict[str, Any]) -> None:
        line = json.dumps(response, ensure_ascii=False)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def _send_error(self, req_id: Any, code: int, message: str) -> None:
        self._send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        })

    def _handle_request(self, req: Dict[str, Any]) -> None:
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        # Handle notifications (no id)
        if req_id is None:
            return

        if method == "initialize":
            self._send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "jira-management",
                        "version": "1.0.0",
                    },
                },
            })

        elif method == "ping":
            self._send_response({"jsonrpc": "2.0", "id": req_id, "result": {}})

        elif method == "tools/list":
            self._send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS_DEFINITIONS},
            })

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                result_data = execute_tool(tool_name, tool_args)
                text_content = json.dumps(result_data, indent=2, ensure_ascii=False)
                self._send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text_content}],
                        "isError": False,
                    },
                })
            except Exception as e:
                self._send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                        "isError": True,
                    },
                })

        elif method == "prompts/list":
            self._send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "prompts": [
                        {
                            "name": "jira_agile_lifecycle",
                            "description": "Rules for sequential agile board progression and DoD gates.",
                        }
                    ]
                },
            })

        elif method == "prompts/get":
            prompt_name = params.get("name")
            if prompt_name == "jira_agile_lifecycle":
                self._send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "description": "Agile Lifecycle & DoD Gate Rules",
                        "messages": [
                            {
                                "role": "user",
                                "content": {
                                    "type": "text",
                                    "text": (
                                        "Follow the 5 mandatory stages: Backlog (1) -> To Do (2) -> "
                                        "In Progress (3) -> In Review (4) -> Done (5). Never skip stages. "
                                        "Always attach automated test verification when moving to Done."
                                    ),
                                },
                            }
                        ],
                    },
                })
            else:
                self._send_error(req_id, -32601, f"Prompt not found: {prompt_name}")

        else:
            self._send_error(req_id, -32601, f"Method not found: {method}")


def run_mcp_server() -> None:
    """Run the stdio MCP server."""
    server = McpServer()
    server.run_stdio()


if __name__ == "__main__":
    run_mcp_server()
