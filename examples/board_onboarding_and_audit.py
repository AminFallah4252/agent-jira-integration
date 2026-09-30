#!/usr/bin/env python3
"""
Example: Board Onboarding & Compliance Audit
--------------------------------------------
Demonstrates how to programmatically verify and audit a Jira board against
the Skill Ordered Board Standard using the jira-management SDK.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from jira_cli import JiraClient, audit_board_compliance, resolve_credentials


def main():
    print("--- Jira Board Onboarding & Audit Example ---")
    creds = resolve_credentials()
    if not creds.get("url") or not creds.get("token"):
        print("[!] No credentials found. Run 'jira auth set' first.")
        sys.exit(1)

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))
    board_id = creds.get("board_id")

    if not board_id:
        print("[*] No default board_id found. Fetching boards for project...")
        boards = client.list_boards(project_key_or_id=creds.get("project"))
        if not boards:
            print("[!] No boards found.")
            sys.exit(1)
        board_id = boards[0]["id"]
        print(f"[*] Selected Board: '{boards[0]['name']}' (ID: {board_id})")

    print(f"[*] Auditing Board ID: {board_id} against Skill Ordered Standard...")
    config = client.get_board_configuration(board_id)
    report = audit_board_compliance(config)

    print(f"\nAudit Report for '{report.get('board_name')}':")
    print(f"  Compliance Score : {report.get('compliance_score')}")
    print(f"  Compliant Status : {'PASSED' if report.get('compliant') else 'FAILED'}")

    print("\nDetected Columns & Stage Mapping:")
    for st in report.get("detected_stages", []):
        print(f"  Stage {st['order']}: {st['stage']:<15} (Column: '{st['column_name']}')")

    if report.get("missing_stages"):
        print(f"\n[!] Missing Mandatory Stages: {', '.join(report.get('missing_stages'))}")

    if report.get("deductions"):
        print("\nAudit Findings:")
        for d in report.get("deductions", []):
            print(f"  - {d}")


if __name__ == "__main__":
    main()
