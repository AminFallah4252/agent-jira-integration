"""Command-line interface and dispatch handlers for Jira Management."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from .adf import adf_to_text
from .client import JiraApiError, JiraClient
from .constants import ORDERED_STAGES
from .credentials import (
    mask_token,
    remove_credentials_from_cache,
    resolve_credentials,
    save_credentials_to_cache,
)
from .workflow import (
    audit_board_compliance,
    map_status_to_standard_stage,
    validate_issue_transition_order,
)

# Force UTF-8 stream encoding across all operating systems & Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass


def print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def print_success(msg: str) -> None:
    print(f"[OK] {msg}")


def print_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def print_warning(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def handle_auth_cmd(args: argparse.Namespace) -> int:
    """Handle 'auth' commands."""
    sub = args.auth_action

    if sub == "set":
        url = args.url
        email = args.email
        token = args.token
        profile = args.profile or "default"
        is_global = args.is_global
        project = args.project
        board_id = args.board_id

        if not url or not token:
            print_error("Both --url and --token are required to configure Jira.")
            return 1

        user_info = None
        if not args.no_verify:
            print(f"[*] Verifying credentials against {url}...")
            client = JiraClient(url, token, email=email)
            try:
                user_info = client.get_myself()
                print_success(f"Authenticated as: {user_info.get('displayName')} ({user_info.get('emailAddress') or user_info.get('accountId')})")
            except Exception as e:
                print_error(f"Live verification failed: {e}")
                print_error("Configuration not saved. Use --no-verify to bypass verification.")
                return 1

        saved_path = save_credentials_to_cache(
            url=url,
            email=email,
            token=token,
            project=project,
            board_id=board_id,
            profile=profile,
            is_global=is_global,
            user_info=user_info
        )
        print_success(f"Credentials successfully saved to {saved_path} (Profile: {profile})")
        print(f"Masked Token: {mask_token(token)}")
        if project:
            print(f"Default Project: {project.upper()}")
        if board_id:
            print(f"Default Board ID: {board_id}")
        return 0

    elif sub == "status":
        profile = args.profile or "default"
        creds = resolve_credentials(profile=profile)
        if not creds.get("url") or not creds.get("token"):
            if args.json:
                print(json.dumps({"authenticated": False, "error": "No credentials resolved"}, indent=2))
            else:
                print_warning(f"No Jira credentials resolved for profile '{profile}'.")
                print("Run 'jira auth set --url <URL> --email <EMAIL> --token <TOKEN>' to configure.")
            return 1

        client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))
        status_data: Dict[str, Any] = {
            "authenticated": False,
            "url": creds["url"],
            "email": creds.get("email"),
            "masked_token": mask_token(creds.get("token")),
            "source": creds.get("source"),
            "default_project": creds.get("project"),
            "default_board_id": creds.get("board_id")
        }

        try:
            myself = client.get_myself()
            status_data["authenticated"] = True
            status_data["user"] = {
                "display_name": myself.get("displayName"),
                "account_id": myself.get("accountId"),
                "email_address": myself.get("emailAddress"),
                "active": myself.get("active", True),
                "account_type": myself.get("accountType")
            }
        except Exception as e:
            status_data["error"] = str(e)

        if args.json:
            print(json.dumps(status_data, indent=2))
            return 0 if status_data["authenticated"] else 1

        print_header("Jira Authentication & Profile Status")
        print(f"Resolution Source : {status_data['source']}")
        print(f"Base URL          : {status_data['url']}")
        print(f"Account Email     : {status_data['email'] or '<none (Bearer PAT)>'}")
        print(f"Masked Token      : {status_data['masked_token']}")
        print(f"Default Project   : {status_data['default_project'] or '<none>'}")
        print(f"Default Board ID  : {status_data['default_board_id'] or '<none>'}")

        if status_data["authenticated"]:
            u = status_data["user"]
            print_success("Status            : Active & Connected")
            print(f"User Name         : {u['display_name']}")
            print(f"Account ID        : {u['account_id']}")
        else:
            print_error(f"Status            : Failed ({status_data.get('error')})")
            return 1
        return 0

    elif sub == "remove":
        profile = args.profile or "default"
        is_global = args.is_global
        removed = remove_credentials_from_cache(profile=profile, is_global=is_global)
        if removed:
            print_success(f"Removed profile '{profile}' from cache.")
            return 0
        else:
            print_warning(f"Profile '{profile}' was not found in cache.")
            return 1

    return 0


def handle_board_cmd(args: argparse.Namespace) -> int:
    """Handle 'board' commands."""
    sub = args.board_action
    creds = resolve_credentials(profile=args.profile or "default")
    if not creds.get("url") or not creds.get("token"):
        print_error("No Jira credentials resolved. Run 'jira auth set' first.")
        return 1

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    if sub == "list":
        proj = args.project or creds.get("project")
        boards = client.list_boards(project_key_or_id=proj, board_type=args.type)
        if args.json:
            print(json.dumps(boards, indent=2))
            return 0

        print_header(f"Agile Boards {f'(Project: {proj})' if proj else ''}")
        if not boards:
            print("No boards found.")
            return 0
        for b in boards:
            print(f"• ID: {b.get('id'):<5} | Type: {b.get('type'):<7} | Name: {b.get('name')}")
        return 0

    elif sub == "get":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1
        b = client.get_board(board_id)
        if args.json:
            print(json.dumps(b, indent=2))
            return 0
        print_header(f"Board Details (ID: {board_id})")
        print(f"Name : {b.get('name')}")
        print(f"Type : {b.get('type')}")
        print(f"URL  : {b.get('self')}")
        return 0

    elif sub == "config":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1
        cfg = client.get_board_configuration(board_id)
        if args.json:
            print(json.dumps(cfg, indent=2))
            return 0
        print_header(f"Board Configuration (ID: {board_id})")
        cols = cfg.get("columnConfig", {}).get("columns", [])
        for idx, c in enumerate(cols, start=1):
            st_names = [s.get("id") or s.get("name", "") for s in c.get("statuses", [])]
            print(f"{idx}. {c.get('name')} -> Statuses: {', '.join(st_names)}")
        return 0

    elif sub == "audit":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1

        cfg = client.get_board_configuration(board_id)
        audit_res = audit_board_compliance(cfg)

        if args.json:
            print(json.dumps(audit_res, indent=2))
            return 0 if audit_res["compliant"] else 1

        print_header(f"Board Workflow Order Audit (ID: {board_id})")
        print(f"Board Name       : {audit_res.get('board_name')}")
        print(f"Compliance Score : {audit_res.get('compliance_score')}")
        print(f"Status           : {'[COMPLIANT]' if audit_res['compliant'] else '[NON-COMPLIANT]'}")

        print("\nOrdered Stages Detected:")
        for st in audit_res.get("detected_stages", []):
            print(f"  Stage {st['order']}: {st['stage']} (Column: '{st['column_name']}')")

        if audit_res.get("missing_stages"):
            print_warning(f"\nMissing Standard Stages: {', '.join(audit_res['missing_stages'])}")
            print("To comply with the skill standard, ensure columns exist for:")
            for s in ORDERED_STAGES:
                print(f"  {s['order']}. {s['stage']}: {s['description']}")

        if audit_res.get("deductions"):
            print("\nFindings & Violations:")
            for d in audit_res["deductions"]:
                print(f"  - {d}")

        return 0 if audit_res["compliant"] else 1

    elif sub == "view":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1

        issues = client.get_board_issues(board_id, max_results=100)

        # Bucket issues by standard stages
        buckets: Dict[str, List[Dict[str, Any]]] = {s["stage"]: [] for s in ORDERED_STAGES}
        other_bucket: List[Dict[str, Any]] = []

        for issue in issues:
            fields = issue.get("fields", {})
            st_name = fields.get("status", {}).get("name", "")
            stage_def = map_status_to_standard_stage(st_name)
            item = {
                "key": issue.get("key"),
                "summary": fields.get("summary", ""),
                "status": st_name,
                "priority": fields.get("priority", {}).get("name", "Medium"),
                "assignee": (fields.get("assignee") or {}).get("displayName", "Unassigned")
            }
            if stage_def:
                buckets[stage_def["stage"]].append(item)
            else:
                other_bucket.append(item)

        if args.json:
            print(json.dumps({"board_id": board_id, "stages": buckets, "other": other_bucket}, indent=2))
            return 0

        print_header(f"Standard Ordered Board View (Board ID: {board_id})")
        for s in ORDERED_STAGES:
            stage_name = s["stage"]
            stage_issues = buckets[stage_name]
            print(f"\n[ STAGE {s['order']}: {stage_name.upper()} ] ({len(stage_issues)} items)")
            print(f"  {s['description']}")
            print("  " + "-" * 60)
            if not stage_issues:
                print("  (empty)")
            for itm in stage_issues:
                print(f"  • [{itm['key']}] {itm['summary'][:50]:<52} | {itm['priority']:<6} | {itm['assignee']}")

        if other_bucket:
            print(f"\n[ UNMAPPED STATUSES ] ({len(other_bucket)} items)")
            print("  " + "-" * 60)
            for itm in other_bucket:
                print(f"  • [{itm['key']}] {itm['summary'][:50]:<52} | Status: {itm['status']}")

        return 0

    return 0


def handle_issue_cmd(args: argparse.Namespace) -> int:
    """Handle 'issue' commands."""
    sub = args.issue_action
    creds = resolve_credentials(profile=args.profile or "default")
    if not creds.get("url") or not creds.get("token"):
        print_error("No Jira credentials resolved. Run 'jira auth set' first.")
        return 1

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    if sub == "create":
        proj = args.project or creds.get("project")
        if not proj:
            print_error("Missing --project argument (or default project in cache).")
            return 1
        summary = args.summary
        if not summary:
            print_error("Missing --summary argument.")
            return 1

        labels = [l.strip() for l in args.labels.split(",")] if args.labels else None
        res = client.create_issue(
            project_key=proj,
            summary=summary,
            issue_type=args.type or "Task",
            description=args.description,
            priority=args.priority,
            assignee_account_id=args.assignee,
            labels=labels,
            parent_key=args.parent
        )

        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print_success(f"Issue created successfully: {res.get('key')} (ID: {res.get('id')})")
        print(f"URL: {creds['url']}/browse/{res.get('key')}")
        return 0

    elif sub == "get":
        key = args.key
        if not key:
            print_error("Missing --key argument.")
            return 1

        issue = client.get_issue(key, expand="names,renderedFields")
        if args.json:
            print(json.dumps(issue, indent=2))
            return 0

        fields = issue.get("fields", {})
        print_header(f"Issue {issue.get('key')}: {fields.get('summary')}")
        print(f"Type     : {fields.get('issuetype', {}).get('name')}")
        print(f"Status   : {fields.get('status', {}).get('name')}")
        print(f"Priority : {fields.get('priority', {}).get('name')}")
        print(f"Assignee : {(fields.get('assignee') or {}).get('displayName', 'Unassigned')}")
        labels = fields.get("labels", [])
        if labels:
            print(f"Labels   : {', '.join(labels)}")

        desc_raw = fields.get("description")
        desc_text = adf_to_text(desc_raw) if isinstance(desc_raw, dict) else (desc_raw or "")
        if desc_text.strip():
            print("\nDescription:")
            print(desc_text.strip())

        return 0

    elif sub == "transition":
        key = args.key
        to_status = args.to
        if not key or not to_status:
            print_error("Both --key and --to are required.")
            return 1

        # Read DoD report if file path provided
        dod_comment = args.comment or ""
        has_dod = bool(dod_comment.strip() or args.dod_report)
        if args.dod_report:
            p = Path(args.dod_report)
            if p.exists() and p.is_file():
                try:
                    dod_comment = f"{dod_comment}\n\n### Definition of Done (DoD) Verification Report\n" + p.read_text(encoding="utf-8")
                except Exception as e:
                    print_warning(f"Could not read DoD report file: {e}")
            else:
                dod_comment = f"{dod_comment}\n\n### Definition of Done (DoD) Verification Report\n{args.dod_report}"

        # Fetch current issue status
        issue = client.get_issue(key)
        curr_status = issue.get("fields", {}).get("status", {}).get("name", "")

        # Validate sequential transition ordering
        valid, err = validate_issue_transition_order(
            current_status=curr_status,
            target_status=to_status,
            has_dod_report=has_dod,
            force=args.force
        )

        if not valid:
            print_error(f"Ordered Transition Blocked: {err}")
            print_error("Use --force to override skill ordering restrictions if strictly required by human supervisor.")
            return 1

        # Find matching transition ID from Jira
        transitions = client.get_transitions(key)
        matching_t = None
        for t in transitions:
            t_name = t.get("name", "").strip().lower()
            to_name = t.get("to", {}).get("name", "").strip().lower()
            req_name = to_status.strip().lower()
            if req_name == t_name or req_name == to_name or req_name in to_name:
                matching_t = t
                break

        if not matching_t:
            available = [f"'{t.get('name')}' -> '{t.get('to', {}).get('name')}' (ID: {t.get('id')})" for t in transitions]
            print_error(f"No transition found matching '{to_status}'.")
            print(f"Available transitions for {key}:\n  " + "\n  ".join(available))
            return 1

        client.transition_issue(key, matching_t["id"], comment=dod_comment if dod_comment.strip() else None)
        print_success(f"Issue {key} transitioned from '{curr_status}' to '{matching_t.get('to', {}).get('name')}'")
        return 0

    elif sub == "comment":
        key = args.key
        body = args.body
        if not key or not body:
            print_error("Both --key and --body are required.")
            return 1
        res = client.add_comment(key, body)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0
        print_success(f"Comment added to {key}.")
        return 0

    elif sub == "worklog":
        key = args.key
        time_spent = args.time
        if not key or not time_spent:
            print_error("Both --key and --time are required (e.g. --time '2h 30m').")
            return 1
        res = client.add_worklog(key, time_spent, comment=args.comment)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0
        print_success(f"Logged {time_spent} work on {key}.")
        return 0

    elif sub == "search":
        jql = args.jql
        if not jql:
            proj = creds.get("project")
            if proj:
                jql = f"project = {proj} ORDER BY updated DESC"
            else:
                print_error("Missing --jql argument.")
                return 1

        res = client.search_issues(jql, max_results=args.limit or 20)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        issues = res.get("issues", [])
        print_header(f"JQL Search: {jql} (Total: {res.get('total')})")
        if not issues:
            print("No issues found.")
            return 0

        for itm in issues:
            f = itm.get("fields", {})
            st = f.get("status", {}).get("name", "")
            prio = f.get("priority", {}).get("name", "")
            print(f"• [{itm.get('key'):<10}] {f.get('summary', '')[:50]:<52} | {st:<15} | {prio}")

        return 0

    return 0


def handle_sprint_cmd(args: argparse.Namespace) -> int:
    """Handle 'sprint' commands."""
    sub = args.sprint_action
    creds = resolve_credentials(profile=args.profile or "default")
    if not creds.get("url") or not creds.get("token"):
        print_error("No Jira credentials resolved. Run 'jira auth set' first.")
        return 1

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    if sub == "list":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1

        sprints = client.list_sprints(board_id, state=args.state)
        if args.json:
            print(json.dumps(sprints, indent=2))
            return 0

        print_header(f"Sprints for Board {board_id}")
        if not sprints:
            print("No sprints found.")
            return 0
        for s in sprints:
            print(f"• ID: {s.get('id'):<5} | State: {s.get('state'):<8} | Name: {s.get('name')}")
        return 0

    elif sub == "issues":
        sprint_id = args.sprint_id
        if not sprint_id:
            print_error("Missing --sprint-id argument.")
            return 1

        issues = client.get_sprint_issues(sprint_id)
        if args.json:
            print(json.dumps(issues, indent=2))
            return 0

        print_header(f"Sprint {sprint_id} Issues ({len(issues)} items)")
        for itm in issues:
            f = itm.get("fields", {})
            print(f"• [{itm.get('key'):<10}] {f.get('summary', '')[:50]:<52} | {f.get('status', {}).get('name')}")
        return 0

    elif sub == "create":
        board_id = args.board_id or creds.get("board_id")
        if not board_id or not args.name:
            print_error("Both --board-id and --name are required.")
            return 1

        sprint = client.create_sprint(
            board_id=board_id,
            name=args.name,
            start_date=args.start_date,
            end_date=args.end_date,
            goal=args.goal
        )
        if args.json:
            print(json.dumps(sprint, indent=2))
            return 0
        print_success(f"Sprint created: {sprint.get('name')} (ID: {sprint.get('id')})")
        return 0

    return 0


def handle_project_cmd(args: argparse.Namespace) -> int:
    """Handle 'project' commands."""
    sub = args.project_action
    creds = resolve_credentials(profile=args.profile or "default")
    if not creds.get("url") or not creds.get("token"):
        print_error("No Jira credentials resolved. Run 'jira auth set' first.")
        return 1

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    if sub == "list":
        projects = client.list_projects()
        if args.json:
            print(json.dumps(projects, indent=2))
            return 0
        print_header("Accessible Jira Projects")
        for p in projects:
            print(f"• Key: {p.get('key'):<8} | Name: {p.get('name')}")
        return 0

    elif sub == "get":
        key = args.key or creds.get("project")
        if not key:
            print_error("Missing --key argument.")
            return 1
        p = client.get_project(key)
        if args.json:
            print(json.dumps(p, indent=2))
            return 0
        print_header(f"Project {p.get('key')}: {p.get('name')}")
        print(f"Lead     : {(p.get('lead') or {}).get('displayName', 'Unknown')}")
        print(f"Category : {(p.get('projectCategory') or {}).get('name', 'None')}")
        return 0

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jira",
        description="Cross-Platform Jira Management CLI & Skill Engine (Zero-Leak Security & Enforced Board Ordering)"
    )
    parser.add_argument("--profile", default="default", help="Credential profile name (default: 'default')")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Auth command
    p_auth = subparsers.add_parser("auth", help="Manage Jira authentication, profiles, and cached credentials")
    s_auth = p_auth.add_subparsers(dest="auth_action", required=True)

    p_auth_set = s_auth.add_parser("set", help="Save credentials to cache")
    p_auth_set.add_argument("--url", required=True, help="Jira base URL (e.g. https://company.atlassian.net)")
    p_auth_set.add_argument("--token", required=True, help="API token (Cloud) or Personal Access Token (Server/DC)")
    p_auth_set.add_argument("--email", help="Account email (required for Atlassian Cloud Basic Auth)")
    p_auth_set.add_argument("--project", help="Default project key (e.g. DEV, PROJ)")
    p_auth_set.add_argument("--board-id", type=int, help="Default agile board ID")
    p_auth_set.add_argument("--global", dest="is_global", action="store_true", help="Save to global config ~/.gemini/config/jira.json")
    p_auth_set.add_argument("--no-verify", action="store_true", help="Skip live connection test")

    s_auth.add_parser("status", help="Test connection and view active credential details (Zero-Leak masked)")
    p_auth_rem = s_auth.add_parser("remove", help="Remove cached credentials")
    p_auth_rem.add_argument("--global", dest="is_global", action="store_true", help="Remove from global cache")

    # 2. Board command
    p_board = subparsers.add_parser("board", help="Manage and audit agile boards according to skill ordering rules")
    s_board = p_board.add_subparsers(dest="board_action", required=True)

    p_board_list = s_board.add_parser("list", help="List agile boards")
    p_board_list.add_argument("--project", help="Filter by project key")
    p_board_list.add_argument("--type", choices=["kanban", "scrum"], help="Filter by board type")

    p_board_get = s_board.add_parser("get", help="Get board details")
    p_board_get.add_argument("--board-id", type=int, help="Board ID (or default from cache)")

    p_board_cfg = s_board.add_parser("config", help="Get board column configuration")
    p_board_cfg.add_argument("--board-id", type=int, help="Board ID")

    p_board_audit = s_board.add_parser("audit", help="Audit board columns against the Skill Ordered Standard")
    p_board_audit.add_argument("--board-id", type=int, help="Board ID to audit")

    p_board_view = s_board.add_parser("view", help="View board issues grouped into the 5 standard ordered stages")
    p_board_view.add_argument("--board-id", type=int, help="Board ID")

    # 3. Issue command
    p_issue = subparsers.add_parser("issue", help="Manage issue lifecycle, transitions, and DoD gates")
    s_issue = p_issue.add_subparsers(dest="issue_action", required=True)

    p_issue_create = s_issue.add_parser("create", help="Create a new Jira issue")
    p_issue_create.add_argument("--summary", required=True, help="Issue summary/title")
    p_issue_create.add_argument("--project", help="Project key (or default from cache)")
    p_issue_create.add_argument("--type", default="Task", help="Issue type (Task, Bug, Story, Epic)")
    p_issue_create.add_argument("--description", help="Issue description text or markdown")
    p_issue_create.add_argument("--priority", help="Priority (Lowest, Low, Medium, High, Highest)")
    p_issue_create.add_argument("--assignee", help="Assignee account ID")
    p_issue_create.add_argument("--labels", help="Comma-separated labels")
    p_issue_create.add_argument("--parent", help="Parent issue key (for sub-tasks)")

    p_issue_get = s_issue.add_parser("get", help="Get issue details")
    p_issue_get.add_argument("--key", required=True, help="Issue key (e.g. PROJ-123)")

    p_issue_trans = s_issue.add_parser("transition", help="Transition issue status enforcing ordered progression")
    p_issue_trans.add_argument("--key", required=True, help="Issue key")
    p_issue_trans.add_argument("--to", required=True, help="Target status or transition name")
    p_issue_trans.add_argument("--comment", help="Transition comment")
    p_issue_trans.add_argument("--dod-report", help="Path to DoD report file or text verification evidence")
    p_issue_trans.add_argument("--force", action="store_true", help="Bypass sequential workflow order checks")

    p_issue_comm = s_issue.add_parser("comment", help="Add a comment to an issue")
    p_issue_comm.add_argument("--key", required=True, help="Issue key")
    p_issue_comm.add_argument("--body", required=True, help="Comment body text or markdown")

    p_issue_work = s_issue.add_parser("worklog", help="Log work on an issue")
    p_issue_work.add_argument("--key", required=True, help="Issue key")
    p_issue_work.add_argument("--time", required=True, help="Time spent (e.g. '1h 30m', '4h')")
    p_issue_work.add_argument("--comment", help="Worklog description")

    p_issue_search = s_issue.add_parser("search", help="Search issues via JQL")
    p_issue_search.add_argument("--jql", help="JQL query string")
    p_issue_search.add_argument("--limit", type=int, default=20, help="Max results")

    # 4. Sprint command
    p_sprint = subparsers.add_parser("sprint", help="Manage sprints for Scrum boards")
    s_sprint = p_sprint.add_subparsers(dest="sprint_action", required=True)

    p_sprint_list = s_sprint.add_parser("list", help="List sprints for a board")
    p_sprint_list.add_argument("--board-id", type=int, help="Board ID")
    p_sprint_list.add_argument("--state", choices=["active", "future", "closed"], help="Sprint state")

    p_sprint_issues = s_sprint.add_parser("issues", help="List issues in a sprint")
    p_sprint_issues.add_argument("--sprint-id", type=int, required=True, help="Sprint ID")

    p_sprint_create = s_sprint.add_parser("create", help="Create a sprint")
    p_sprint_create.add_argument("--board-id", type=int, help="Board ID")
    p_sprint_create.add_argument("--name", required=True, help="Sprint name")
    p_sprint_create.add_argument("--start-date", help="ISO start date")
    p_sprint_create.add_argument("--end-date", help="ISO end date")
    p_sprint_create.add_argument("--goal", help="Sprint goal")

    # 5. Project command
    p_proj = subparsers.add_parser("project", help="Inspect Jira projects")
    s_proj = p_proj.add_subparsers(dest="project_action", required=True)
    s_proj.add_parser("list", help="List projects")
    p_proj_get = s_proj.add_parser("get", help="Get project details")
    p_proj_get.add_argument("--key", help="Project key")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "auth": handle_auth_cmd,
        "board": handle_board_cmd,
        "issue": handle_issue_cmd,
        "sprint": handle_sprint_cmd,
        "project": handle_project_cmd
    }

    handler = handlers.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    try:
        exit_code = handler(args)
        sys.exit(exit_code or 0)
    except JiraApiError as e:
        if args.json:
            print(json.dumps({"error": str(e), "status_code": e.status_code, "data": e.response_data}, indent=2))
        else:
            print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Operation cancelled by user]")
        sys.exit(130)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": f"Unhandled error: {str(e)}"}, indent=2))
        else:
            print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)
