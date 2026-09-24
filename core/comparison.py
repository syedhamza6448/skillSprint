"""
core/comparison.py  —  Phase 7: Comparison Engine & Verification Status

Composes Pipeline 1 (generate_plan) and Pipeline 2 (validate) into a single
comparison result that:
  - Builds a per-requirement verification table for every mandatory matrix row
  - Assigns a fine-grained item_status per requirement
  - Assigns an overall plan-level status distinguishable from a plain "Fail"
  - Persists the result via log_comparison()
  - Returns everything callers need for the UI
"""

from core.genai_pipeline import generate_plan
from core.validation_pipeline import validate
from core import db

# ── Item-level status vocabulary (Phase 7 / PHASES.md) ──────────────────────
STATUS_VERIFIED              = "Verified"
STATUS_VERIFIED_WARNING      = "Verified with Warning"
STATUS_PARTIALLY_VERIFIED    = "Partially Verified"
STATUS_SOURCE_MISSING        = "Source Support Missing"
STATUS_REQ_MISSING           = "Requirement Missing"
STATUS_UNSUPPORTED           = "Unsupported Requirement"
STATUS_OUTDATED              = "Outdated Source"
STATUS_CONTRADICTION         = "Contradiction Detected"
STATUS_MANUAL_REVIEW         = "Manual Review Required"

# ── Overall plan-level status vocabulary ─────────────────────────────────────
OVERALL_PASS                 = "Pass"
OVERALL_WARNING              = "Warning"
OVERALL_FAIL                 = "Fail"
OVERALL_GEN_FAILED           = "Generation Failed"


def _item_status(covered: bool, flag_types: list) -> str:
    """Map coverage + flag types onto a single human-readable item status."""
    if not covered:
        return STATUS_REQ_MISSING

    flag_set = set(flag_types)

    # Priority order: most severe first
    if "Unsupported-claim" in flag_set:
        return STATUS_UNSUPPORTED
    if "Outdated-policy" in flag_set and "Duplicate" in flag_set:
        return STATUS_MANUAL_REVIEW
    if "Outdated-policy" in flag_set:
        return STATUS_OUTDATED
    if "Duplicate" in flag_set or "Sequence-violation" in flag_set:
        return STATUS_VERIFIED_WARNING
    if "Missing-mandatory" in flag_set:
        # Covered=True but also in missing_mandatory? Shouldn't happen, guard anyway
        return STATUS_PARTIALLY_VERIFIED

    return STATUS_VERIFIED


def compare(employee_id: str, role: str) -> dict:
    """
    Run Pipeline 1 (GenAI generation) then Pipeline 2 (ground-truth validation)
    and merge results into a structured comparison dict.

    Returns
    -------
    {
        employee_id, role, overall_status, model_used,
        per_requirement: [
            { requirement_id, requirement_text, covered, flags, item_status }
        ],
        pipeline1_output,   # the raw plan dict (or error dict)
        pipeline2_output,   # the raw validation result dict
    }
    """
    # ── 1. Pipeline 1 — generate the plan ───────────────────────────────────
    p1_raw = generate_plan(employee_id, role)

    if "error" in p1_raw:
        result = {
            "employee_id":      employee_id,
            "role":             role,
            "overall_status":   OVERALL_GEN_FAILED,
            "model_used":       None,
            "per_requirement":  [],
            "pipeline1_output": p1_raw,
            "pipeline2_output": None,
        }
        db.log_comparison(employee_id, role, OVERALL_GEN_FAILED,
                          coverage_score=0.0, traceability_score=0.0,
                          flags_json=str([]))
        return result

    plan_dict  = p1_raw["plan"]
    model_used = p1_raw.get("model_used")

    # ── 2. Pipeline 2 — validate the plan ───────────────────────────────────
    p2 = validate(employee_id, role, plan_dict)

    # ── 3. Build per-requirement comparison table ────────────────────────────
    matrix_rows   = db.get_matrix_rows_for_role(role)
    mandatory_rows = [r for r in matrix_rows if r["mandatory"] == "Y"]

    # Index generated modules by requirement_id for O(1) lookup
    generated_req_ids = {
        mod["requirement_id"]
        for mod in plan_dict.get("modules", [])
        if mod.get("requirement_id")
    }

    # Index flags from Pipeline 2 by requirement_id
    flags_by_req: dict[str, list[dict]] = {}
    for flag in p2.get("flags", []):
        rid = flag.get("requirement_id")
        if rid:
            flags_by_req.setdefault(rid, []).append(flag)

    per_requirement = []
    for row in mandatory_rows:
        rid       = row["requirement_id"]
        covered   = rid in generated_req_ids
        req_flags = flags_by_req.get(rid, [])
        ftypes    = [f["type"] for f in req_flags]

        per_requirement.append({
            "requirement_id":   rid,
            "requirement_text": row.get("requirement_text", ""),
            "source_section":   row.get("source_section", ""),
            "covered":          covered,
            "flags":            req_flags,
            "item_status":      _item_status(covered, ftypes),
        })

    # ── 4. Overall plan-level status ─────────────────────────────────────────
    # Start from Pipeline 2's verdict, then refine with comparison-level nuance.
    p2_status      = p2.get("status", OVERALL_FAIL)
    has_unsupported = any(r["item_status"] == STATUS_UNSUPPORTED for r in per_requirement)
    has_missing     = any(r["item_status"] == STATUS_REQ_MISSING  for r in per_requirement)
    has_outdated    = any(r["item_status"] == STATUS_OUTDATED      for r in per_requirement)
    has_duplicate   = any(r["item_status"] == STATUS_VERIFIED_WARNING for r in per_requirement)

    if has_unsupported or has_missing:
        overall_status = OVERALL_FAIL
    elif p2_status == OVERALL_FAIL:
        overall_status = OVERALL_FAIL
    elif has_outdated or has_duplicate or p2_status == OVERALL_WARNING:
        overall_status = OVERALL_WARNING
    else:
        overall_status = OVERALL_PASS

    # ── 5. Persist ───────────────────────────────────────────────────────────
    import json
    db.log_comparison(
        employee_id=employee_id,
        role=role,
        overall_status=overall_status,
        coverage_score=p2.get("coverage_score", 0.0),
        traceability_score=p2.get("traceability_score", 0.0),
        flags_json=json.dumps(p2.get("flags", [])),
    )

    return {
        "employee_id":      employee_id,
        "role":             role,
        "overall_status":   overall_status,
        "model_used":       model_used,
        "per_requirement":  per_requirement,
        "pipeline1_output": plan_dict,
        "pipeline2_output": p2,
    }
