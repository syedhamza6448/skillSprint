import difflib
from core import db

STAGE_RANK = {
    "day 1": 1, "day1": 1,
    "week 1": 2, "week1": 2,
    "week 2": 3, "week2": 3,
    "week 3": 4, "week3": 4,
    "week 4": 5, "week4": 5,
    "month 1": 6, "month1": 6,
    "month 2": 7, "month2": 7,
    "month 3": 8, "month3": 8,
}

def parse_stage_rank(stage_str: str) -> int:
    if not stage_str:
        return 999
    key = str(stage_str).strip().lower()
    return STAGE_RANK.get(key, 999)

def validate(employee_id, role, genai_output: dict) -> dict:
    matrix_rows = db.get_matrix_rows_for_role(role)
    all_matrix_rows_df = db.get_all_requirements_df()
    
    # Pre-process matrix rows for this role
    mandatory_req_ids = set(row['requirement_id'] for row in matrix_rows if row['mandatory'] == 'Y')
    total_mandatory = len(mandatory_req_ids)
    
    # Map requirement_id -> prerequisite_requirement_id for this role
    prereq_map = {
        row['requirement_id']: row.get('prerequisite_requirement_id', '').strip()
        for row in matrix_rows
        if row.get('prerequisite_requirement_id', '') and str(row.get('prerequisite_requirement_id', '')).strip()
    }

    # Build a set of requirement_ids that are THEMSELVES legacy/superseded.
    legacy_req_ids = set()
    for _, row in all_matrix_rows_df.iterrows():
        comp_area = str(row.get('competency_area', '')).lower()
        req_text = str(row.get('requirement_text', ''))
        if comp_area == 'outdated' or '[v0.9]' in req_text:
            legacy_req_ids.add(row['requirement_id'])

    modules = genai_output.get('modules', [])
    total_modules = len(modules)
    
    # Index generated modules by requirement_id -> due_stage
    module_stages_by_req_id = {
        mod.get('requirement_id'): mod.get('due_stage')
        for mod in modules
        if mod.get('requirement_id')
    }

    covered_mandatory_set = set()
    flags = []
    
    doc_section_pairs = []
    for mod in modules:
        if 'source_doc_id' in mod and 'source_section' in mod:
            doc_section_pairs.append((mod['source_doc_id'], mod['source_section']))
    
    valid_chunks = db.get_chunks_for_docs_and_sections(doc_section_pairs)
    valid_citations_set = set((c['doc_id'], c['heading']) for c in valid_chunks)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id FROM documents")
    all_doc_ids = set(row[0] for row in cursor.fetchall())
    conn.close()

    valid_citations = 0
    
    for i, mod in enumerate(modules):
        req_id = mod.get('requirement_id')
        if req_id in mandatory_req_ids:
            covered_mandatory_set.add(req_id)
            
        doc_id = mod.get('source_doc_id')
        section = mod.get('source_section')
        module_name = mod.get('module_name') or req_id or f"Module {i + 1}"
        due_stage = mod.get('due_stage', 'N/A')
        
        # Unsupported-claim detection
        if doc_id not in all_doc_ids:
            flags.append({
                "type": "Unsupported-claim",
                "requirement_id": req_id,
                "module_name": module_name,
                "detail": f"source_doc_id {doc_id} does not exist in documents table"
            })
            
        # Traceability check
        if (doc_id, section) in valid_citations_set:
            valid_citations += 1
            
        # Outdated-policy detection
        if req_id in legacy_req_ids:
            flags.append({
                "type": "Outdated-policy",
                "requirement_id": req_id,
                "module_name": module_name,
                "detail": f"source_section '{section}' appears in a legacy/superseded matrix row"
            })
            
        # Sequence validation: check prerequisite ordering
        prereq_id = prereq_map.get(req_id)
        if prereq_id:
            if prereq_id not in module_stages_by_req_id:
                flags.append({
                    "type": "Sequence-violation",
                    "requirement_id": req_id,
                    "module_name": module_name,
                    "detail": f"Module {module_name} (due {due_stage}) requires prerequisite {prereq_id} which is missing or scheduled later"
                })
            else:
                prereq_stage = module_stages_by_req_id[prereq_id]
                mod_rank = parse_stage_rank(due_stage)
                prereq_rank = parse_stage_rank(prereq_stage)
                if prereq_rank > mod_rank:
                    flags.append({
                        "type": "Sequence-violation",
                        "requirement_id": req_id,
                        "module_name": module_name,
                        "detail": f"Module {module_name} (due {due_stage}) requires prerequisite {prereq_id} which is missing or scheduled later"
                    })

        # Duplicate detection
        for j in range(i + 1, total_modules):
            other_mod = modules[j]
            other_module_name = other_mod.get('module_name')
            
            # check module_name similarity
            name_ratio = difflib.SequenceMatcher(None, str(module_name or ''), str(other_module_name or '')).ratio()
            
            # check tasks similarity
            tasks1 = " ".join(mod.get('tasks', [])) if isinstance(mod.get('tasks'), list) else str(mod.get('tasks', ''))
            tasks2 = " ".join(other_mod.get('tasks', [])) if isinstance(other_mod.get('tasks'), list) else str(other_mod.get('tasks', ''))
            task_ratio = difflib.SequenceMatcher(None, tasks1, tasks2).ratio()
            
            if name_ratio > 0.85 or task_ratio > 0.85:
                flags.append({
                    "type": "Duplicate",
                    "requirement_id": req_id,
                    "module_name": module_name,
                    "detail": f"Near-identical to module '{other_module_name}' (name ratio: {name_ratio:.2f}, task ratio: {task_ratio:.2f})"
                })

    missing_mandatory = list(mandatory_req_ids - covered_mandatory_set)
    
    coverage_score = (len(covered_mandatory_set) / total_mandatory * 100) if total_mandatory > 0 else 100.0
    traceability_score = (valid_citations / total_modules * 100) if total_modules > 0 else 100.0
    
    # Missing-mandatory detection flag
    for missing in missing_mandatory:
        flags.append({
            "type": "Missing-mandatory",
            "requirement_id": missing,
            "module_name": None,
            "detail": f"Mandatory requirement {missing} is missing from output"
        })
        
    has_unsupported_claim = any(f['type'] == 'Unsupported-claim' for f in flags)
    has_warning_flags = any(f['type'] in ['Duplicate', 'Outdated-policy', 'Sequence-violation'] for f in flags)
    
    if coverage_score < 100 or has_unsupported_claim:
        status = "Fail"
    elif has_warning_flags:
        status = "Warning"
    else:
        status = "Pass"
        
    db.log_validation_result(employee_id, role, coverage_score, traceability_score, status)
        
    return {
        "coverage_score": coverage_score,
        "traceability_score": traceability_score,
        "flags": flags,
        "missing_mandatory": missing_mandatory,
        "status": status
    }
