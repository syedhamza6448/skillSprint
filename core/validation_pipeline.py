import difflib
from core import db

def validate(employee_id, role, genai_output: dict) -> dict:
    matrix_rows = db.get_matrix_rows_for_role(role)
    all_matrix_rows_df = db.get_all_requirements_df()
    
    # Pre-process matrix rows for this role
    mandatory_req_ids = set(row['requirement_id'] for row in matrix_rows if row['mandatory'] == 'Y')
    total_mandatory = len(mandatory_req_ids)
    
    # Build a set of requirement_ids that are THEMSELVES legacy/superseded.
    # A row is legacy if its competency_area is 'Outdated' OR its requirement_text
    # contains the '[v0.9]' version tag used throughout the matrix CSV.
    # We check the module's own requirement_id against this set — NOT the
    # source_section — so current-policy modules that happen to cite the same
    # section as a legacy row are never incorrectly flagged.
    legacy_req_ids = set()
    for _, row in all_matrix_rows_df.iterrows():
        comp_area = str(row.get('competency_area', '')).lower()
        req_text = str(row.get('requirement_text', ''))
        if comp_area == 'outdated' or '[v0.9]' in req_text:
            legacy_req_ids.add(row['requirement_id'])

    modules = genai_output.get('modules', [])
    total_modules = len(modules)
    
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
        module_name = mod.get('module_name')
        
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
            
        # Outdated-policy detection: flag only if THIS module's own requirement_id
        # is itself a legacy/superseded row — not because some other row shares
        # the same source_section.
        if req_id in legacy_req_ids:
            flags.append({
                "type": "Outdated-policy",
                "requirement_id": req_id,
                "module_name": module_name,
                "detail": f"source_section '{section}' appears in a legacy/superseded matrix row"
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
    has_warning_flags = any(f['type'] in ['Duplicate', 'Outdated-policy'] for f in flags)
    
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
