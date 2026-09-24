import os

snippet = """
def log_comparison(employee_id, role, overall_status, coverage_score, traceability_score, flags_json):
    conn = get_connection()
    cursor = conn.cursor()
    comparison_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO comparison_results
            (comparison_id, employee_id, role, overall_status, coverage_score, traceability_score, flags_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (comparison_id, employee_id, role, overall_status,
          coverage_score, traceability_score, flags_json))
    conn.commit()
    conn.close()
    return comparison_id
"""

db_path = os.path.join(os.path.dirname(__file__), 'core', 'db.py')
with open(db_path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'def log_comparison' not in content:
    with open(db_path, 'a', encoding='utf-8') as f:
        f.write(snippet)
    print("Appended log_comparison to core/db.py")
else:
    print("log_comparison already present in core/db.py")
