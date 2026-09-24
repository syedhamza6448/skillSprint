def log_comparison(employee_id, role, overall_status, coverage_score, traceability_score, flags_json):
    conn = get_connection()
    cursor = conn.cursor()
    comparison_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO comparison_results
            (comparison_id, employee_id, role, overall_status, coverage_score, traceability_score, flags_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (comparison_id, employee_id, role, overall_status,
          coverage_score, traceability_score, flags_json))
    conn.commit()
    conn.close()
    return comparison_id
