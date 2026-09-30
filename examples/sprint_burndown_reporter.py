#!/usr/bin/env python3
"""
Example: Sprint Ordered Stage Reporter
--------------------------------------
Inspects the active sprint on a board, aggregates issues into the 5 standard
ordered stages, and prints a structured Markdown report.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from jira_cli import ORDERED_STAGES, JiraClient, map_status_to_standard_stage, resolve_credentials


def main():
    creds = resolve_credentials()
    if not creds.get("url") or not creds.get("token"):
        print("[!] No credentials resolved. Configure credentials first.")
        sys.exit(1)

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))
    board_id = creds.get("board_id")
    if not board_id:
        boards = client.list_boards(project_key_or_id=creds.get("project"))
        if not boards:
            print("[!] No boards found.")
            sys.exit(1)
        board_id = boards[0]["id"]

    print(f"[*] Querying Board ID {board_id}...")
    sprints = client.list_sprints(board_id, state="active")
    if not sprints:
        print("[!] No active sprint found on board. Fetching board backlog/issues instead...")
        issues = client.get_board_issues(board_id)
        sprint_name = "Board Overview"
    else:
        active_sprint = sprints[0]
        sprint_name = active_sprint.get("name")
        issues = client.get_sprint_issues(active_sprint["id"])

    # Bucket issues by standard stage
    buckets = {s["stage"]: [] for s in ORDERED_STAGES}
    unmapped = []

    for issue in issues:
        fields = issue.get("fields", {})
        status_name = fields.get("status", {}).get("name", "")
        stage_def = map_status_to_standard_stage(status_name)
        item = {
            "key": issue.get("key"),
            "summary": fields.get("summary", ""),
            "assignee": (fields.get("assignee") or {}).get("displayName", "Unassigned"),
            "priority": (fields.get("priority") or {}).get("name", "Medium")
        }
        if stage_def:
            buckets[stage_def["stage"]].append(item)
        else:
            unmapped.append(item)

    # Output Markdown Report
    print(f"\n# 📊 Agile Sprint Status Report: {sprint_name}")
    print(f"**Total Issues Tracked**: {len(issues)}\n")

    for s in ORDERED_STAGES:
        stage_name = s["stage"]
        items = buckets[stage_name]
        pct = (len(items) / len(issues) * 100) if issues else 0
        print(f"### Stage {s['order']}: {stage_name} ({len(items)} items - {pct:.1f}%)")
        print(f"*{s['description']}*")
        if not items:
            print("- *(No issues in this stage)*")
        else:
            for itm in items:
                print(f"- **[{itm['key']}]** {itm['summary']} `({itm['priority']})` — @{itm['assignee']}")
        print()

    if unmapped:
        print(f"### ⚠️ Unmapped / Non-Standard Statuses ({len(unmapped)} items)")
        for itm in unmapped:
            print(f"- **[{itm['key']}]** {itm['summary']}")
        print()


if __name__ == "__main__":
    main()
