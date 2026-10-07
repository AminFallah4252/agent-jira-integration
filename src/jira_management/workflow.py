"""Enforced board ordering, audit scoring, and sequential transition gates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .constants import ORDERED_STAGES


def map_status_to_standard_stage(status_name: str) -> Optional[Dict[str, Any]]:
    """Map an arbitrary Jira status name to one of the 5 standard skill stages."""
    name_clean = status_name.strip().lower()
    for stage_def in ORDERED_STAGES:
        for common in stage_def["common_statuses"]:
            if name_clean == common or common in name_clean:
                return stage_def
    return None


def audit_board_compliance(board_config: Dict[str, Any]) -> Dict[str, Any]:
    """Audit a board's columns and workflow mapping against the Skill Ordered Standard.
    
    Verifies:
    1. Presence of all 5 ordered stages (Backlog, To Do, In Progress, In Review, Done).
    2. Correct left-to-right sequential column ordering.
    3. Proper mapping of statuses to stages.
    """
    columns = board_config.get("columnConfig", {}).get("columns", [])
    if not columns:
        return {
            "compliant": False,
            "score": 0,
            "error": "No columns found in board configuration."
        }

    detected_stages: List[Dict[str, Any]] = []
    unmapped_columns: List[str] = []

    for idx, col in enumerate(columns):
        col_name = col.get("name", "").strip()
        statuses = col.get("statuses", [])
        status_names = [s.get("id") or s.get("name", "") for s in statuses]

        stage_match = map_status_to_standard_stage(col_name)
        if not stage_match and statuses:
            # Try to match from underlying statuses
            for s in statuses:
                s_name = s.get("name", "")
                stage_match = map_status_to_standard_stage(s_name)
                if stage_match:
                    break

        if stage_match:
            detected_stages.append({
                "column_index": idx,
                "column_name": col_name,
                "stage": stage_match["stage"],
                "order": stage_match["order"],
                "statuses": status_names
            })
        else:
            unmapped_columns.append(col_name)

    # Check order correctness
    detected_orders = [d["order"] for d in detected_stages]
    is_strictly_ordered = detected_orders == sorted(detected_orders)

    # Check stage coverage
    found_orders = set(detected_orders)
    missing_stages = [s["stage"] for s in ORDERED_STAGES if s["order"] not in found_orders]

    score = 100
    deductions = []
    if missing_stages:
        score -= len(missing_stages) * 15
        deductions.append(f"Missing mandatory standard stages: {', '.join(missing_stages)}")
    if not is_strictly_ordered:
        score -= 30
        deductions.append("Board columns violate the mandatory left-to-right workflow ordering.")
    if unmapped_columns:
        score -= len(unmapped_columns) * 5
        deductions.append(f"Columns not conforming to standard naming: {', '.join(unmapped_columns)}")

    score = max(0, score)
    is_compliant = score >= 85 and is_strictly_ordered and not missing_stages

    return {
        "board_id": board_config.get("id"),
        "board_name": board_config.get("name"),
        "compliant": is_compliant,
        "compliance_score": f"{score}%",
        "detected_stages": detected_stages,
        "missing_stages": missing_stages,
        "unmapped_columns": unmapped_columns,
        "deductions": deductions,
        "recommended_order": [s["stage"] for s in ORDERED_STAGES]
    }


def validate_issue_transition_order(
    current_status: str,
    target_status: str,
    has_dod_report: bool = False,
    force: bool = False
) -> Tuple[bool, Optional[str]]:
    """Validate whether an issue transition adheres to the enforced sequential ordering.
    
    Prevents bypassing 'In Progress' or 'In Review' directly to 'Done'.
    """
    if force:
        return True, None

    current_stage = map_status_to_standard_stage(current_status)
    target_stage = map_status_to_standard_stage(target_status)

    if not current_stage or not target_stage:
        # Cannot strictly evaluate unknown statuses
        return True, None

    curr_order = current_stage["order"]
    tgt_order = target_stage["order"]

    # Reopening or moving backwards is permitted (e.g. from Review back to In Progress)
    if tgt_order < curr_order:
        return True, None

    # Forward skip check: Cannot jump straight from Backlog (1) or To Do (2) to Done (5)
    if curr_order <= 2 and tgt_order == 5:
        return False, (
            f"Ordered Workflow Violation: Cannot jump directly from '{current_status}' (Stage {curr_order}) "
            f"to '{target_status}' (Stage 5). Must transition through Stage 3 (In Progress) and "
            f"Stage 4 (In Review / Verification) to satisfy Definition of Done."
        )

    # DoD Check: Transitioning to Done (Stage 5) requires review verification
    if tgt_order == 5 and curr_order != 4:
        return False, (
            f"Ordered Workflow Violation: Issues must be in 'In Review' (Stage 4) before transitioning "
            f"to 'Done' (Stage 5). Current stage is '{current_status}' (Stage {curr_order})."
        )

    if tgt_order == 5 and not has_dod_report:
        return False, (
            "Definition of Done Gate: Transitioning to 'Done' requires verification notes or DoD proof. "
            "Please provide --comment or --dod-report detailing tests and verification evidence."
        )

    return True, None
