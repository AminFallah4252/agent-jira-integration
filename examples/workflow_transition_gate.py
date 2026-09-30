#!/usr/bin/env python3
"""
Example: Enforced Workflow Transition with DoD Verification Gate
---------------------------------------------------------------
Demonstrates how an autonomous agent or developer transitions an issue through
the mandatory sequential stages:
  To Do -> In Progress -> In Review -> Done
and satisfies the Definition of Done (DoD) verification gate.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from jira_cli import JiraClient, resolve_credentials, validate_issue_transition_order


def transition_with_enforcement(client: JiraClient, issue_key: str, target_stage: str, dod_report: str = ""):
    print(f"\n[*] Requesting transition of {issue_key} to '{target_stage}'...")
    issue = client.get_issue(issue_key)
    curr_status = issue.get("fields", {}).get("status", {}).get("name", "")
    print(f"    Current Status: '{curr_status}'")

    has_dod = bool(dod_report.strip())
    valid, err = validate_issue_transition_order(
        current_status=curr_status,
        target_status=target_stage,
        has_dod_report=has_dod,
        force=False
    )

    if not valid:
        print(f"    [X] TRANSITION BLOCKED: {err}")
        return False

    transitions = client.get_transitions(issue_key)
    matching = next((t for t in transitions if target_stage.lower() in t.get("name", "").lower() or target_stage.lower() in t.get("to", {}).get("name", "").lower()), None)

    if not matching:
        print(f"    [X] No transition found matching '{target_stage}'.")
        return False

    client.transition_issue(issue_key, matching["id"], comment=dod_report if dod_report else None)
    print(f"    [OK] Transitioned to '{matching.get('to', {}).get('name')}' successfully.")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python workflow_transition_gate.py <ISSUE_KEY>")
        sys.exit(1)

    issue_key = sys.argv[1].upper()
    creds = resolve_credentials()
    if not creds.get("url") or not creds.get("token"):
        print("[!] No credentials resolved. Configure credentials first.")
        sys.exit(1)

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    print(f"=== Demonstrating Workflow Order for {issue_key} ===")
    
    # 1. Start work: To Do -> In Progress
    transition_with_enforcement(client, issue_key, "In Progress")

    # 2. Complete work: In Progress -> In Review
    transition_with_enforcement(client, issue_key, "In Review")

    # 3. Attempting to jump to Done without DoD report (Demonstrating Gate block)
    print("\n[Step 3: Attempting Done without DoD proof]")
    transition_with_enforcement(client, issue_key, "Done", dod_report="")

    # 4. Successfully transitioning to Done with DoD proof
    dod_proof = (
        "### Automated DoD Verification Report\n"
        "- [x] Unit test suite executed: 42 passed, 0 failed\n"
        "- [x] Static type check: tsc/mypy clean (0 errors)\n"
        "- [x] Git branch merged to main: commit #a1b2c3d\n"
    )
    print("\n[Step 4: Providing DoD proof to pass gate]")
    transition_with_enforcement(client, issue_key, "Done", dod_report=dod_proof)


if __name__ == "__main__":
    main()
