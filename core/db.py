import sqlite3
import os
import csv
import pandas as pd
import uuid

# Put the database in the root of the project
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'skillsprint.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def setup_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            filename TEXT,
            file_type TEXT,
            version TEXT,
            effective_date TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_hash TEXT UNIQUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT,
            section TEXT,
            heading TEXT,
            page INTEGER,
            version TEXT,
            text TEXT,
            FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generation_log (
            log_id TEXT PRIMARY KEY,
            employee_id TEXT,
            role TEXT,
            prompt_version TEXT,
            model TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            error_message TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS validation_results (
            result_id TEXT PRIMARY KEY,
            employee_id TEXT,
            role TEXT,
            coverage_score REAL,
            traceability_score REAL,
            status TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comparison_results (
            comparison_id TEXT PRIMARY KEY,
            employee_id TEXT,
            role TEXT,
            overall_status TEXT,
            coverage_score REAL,
            traceability_score REAL,
            flags_json TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS review_decisions (
            decision_id TEXT PRIMARY KEY,
            comparison_id TEXT,
            employee_id TEXT,
            role TEXT,
            original_status TEXT,
            reviewer_decision TEXT,
            reviewer_notes TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(comparison_id) REFERENCES comparison_results(comparison_id)
        )
    ''')

    cursor.execute("PRAGMA table_info(requirement_matrix)")
    cols = [r[1] for r in cursor.fetchall()]
    conn.commit()
    conn.close()

    if not cols or 'prerequisite_requirement_id' not in cols:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'role_requirement_matrix.csv')
        if os.path.exists(csv_path):
            load_matrix(csv_path)

def insert_document(doc_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO documents (doc_id, filename, file_type, version, effective_date, file_hash)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        doc_data['doc_id'], doc_data['filename'], doc_data['file_type'],
        doc_data['version'], doc_data['effective_date'], doc_data['file_hash']
    ))
    conn.commit()
    conn.close()

def insert_chunks(chunks):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT INTO chunks (chunk_id, doc_id, section, heading, page, version, text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [
        (c['chunk_id'], c['doc_id'], c['section'], c['heading'], c['page'], c['version'], c['text'])
        for c in chunks
    ])
    conn.commit()
    conn.close()

def document_exists(file_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM documents WHERE file_hash = ?', (file_hash,))
    result = cursor.fetchone()
    conn.close()
    return bool(result)

def load_matrix(csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'role_requirement_matrix.csv')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS requirement_matrix')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requirement_matrix (
            requirement_id TEXT PRIMARY KEY,
            role TEXT,
            policy_source_doc TEXT,
            source_section TEXT,
            requirement_text TEXT,
            mandatory TEXT,
            priority TEXT,
            due_stage TEXT,
            competency_area TEXT,
            related_task TEXT,
            related_assessment_topic TEXT,
            prerequisite_requirement_id TEXT
        )
    ''')
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute('''
                INSERT INTO requirement_matrix (
                    requirement_id, role, policy_source_doc, source_section,
                    requirement_text, mandatory, priority, due_stage,
                    competency_area, related_task, related_assessment_topic,
                    prerequisite_requirement_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['requirement_id'], row['role'], row['policy_source_doc'],
                row['source_section'], row['requirement_text'], row['mandatory'],
                row['priority'], row['due_stage'], row['competency_area'],
                row['related_task'], row['related_assessment_topic'],
                row.get('prerequisite_requirement_id', '')
            ))
            
    conn.commit()
    conn.close()

def get_all_requirements_df():
    conn = get_connection()
    df = pd.read_sql_query('SELECT * FROM requirement_matrix', conn)
    conn.close()
    return df

def get_dashboard_metrics():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM documents')
    doc_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM chunks')
    chunk_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM requirement_matrix')
    req_count = cursor.fetchone()[0]
    conn.close()
    return doc_count, chunk_count, req_count

def get_requirements_per_role_df():
    conn = get_connection()
    df = pd.read_sql_query('SELECT role, COUNT(*) as count FROM requirement_matrix GROUP BY role', conn)
    conn.close()
    return df

def get_matrix_rows_for_role(role):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM requirement_matrix WHERE role = ?', (role,))
    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_chunks_for_docs_and_sections(doc_section_pairs):
    if not doc_section_pairs:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    doc_ids = list(set([p[0] for p in doc_section_pairs]))
    if not doc_ids:
        return []
    placeholders = ', '.join(['?'] * len(doc_ids))
    cursor.execute(f'SELECT doc_id, heading, text FROM chunks WHERE doc_id IN ({placeholders})', doc_ids)
    all_chunks = cursor.fetchall()
    conn.close()
    
    valid_pairs = set(doc_section_pairs)
    relevant = []
    for c_doc, c_heading, c_text in all_chunks:
        if (c_doc, c_heading) in valid_pairs:
            relevant.append({'doc_id': c_doc, 'heading': c_heading, 'text': c_text})
    return relevant

def log_generation(employee_id, role, prompt_version, model, status, error_message=""):
    conn = get_connection()
    cursor = conn.cursor()
    log_id = str(uuid.uuid4())
    cursor.execute(
        'INSERT INTO generation_log (log_id, employee_id, role, prompt_version, model, status, error_message) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (log_id, employee_id, role, prompt_version, model, status, error_message)
    )
    conn.commit()
    conn.close()

def log_validation_result(employee_id, role, coverage_score, traceability_score, status):
    conn = get_connection()
    cursor = conn.cursor()
    result_id = str(uuid.uuid4())
    cursor.execute(
        'INSERT INTO validation_results (result_id, employee_id, role, coverage_score, traceability_score, status) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (result_id, employee_id, role, coverage_score, traceability_score, status)
    )
    conn.commit()
    conn.close()
    return result_id

def log_comparison(employee_id, role, overall_status, coverage_score, traceability_score, flags_json):
    conn = get_connection()
    cursor = conn.cursor()
    comparison_id = str(uuid.uuid4())
    cursor.execute(
        'INSERT INTO comparison_results '
        '(comparison_id, employee_id, role, overall_status, coverage_score, traceability_score, flags_json) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (comparison_id, employee_id, role, overall_status,
         coverage_score, traceability_score, flags_json)
    )
    conn.commit()
    conn.close()
    return comparison_id


def log_review_decision(comparison_id, employee_id, role, original_status,
                        reviewer_decision, reviewer_notes=""):
    """Persist a reviewer action without touching the original Pipeline 1/2 output."""
    conn = get_connection()
    cursor = conn.cursor()
    decision_id = str(uuid.uuid4())
    cursor.execute(
        'INSERT INTO review_decisions '
        '(decision_id, comparison_id, employee_id, role, original_status, reviewer_decision, reviewer_notes) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (decision_id, comparison_id, employee_id, role,
         original_status, reviewer_decision, reviewer_notes)
    )
    conn.commit()
    conn.close()
    return decision_id


# ── Dashboard query helpers ────────────────────────────────────────────────────

def get_comparison_results_df():
    """Return all comparison results as a DataFrame, newest first."""
    conn = get_connection()
    df = pd.read_sql_query(
        'SELECT * FROM comparison_results ORDER BY timestamp DESC', conn
    )
    conn.close()
    return df


def get_generation_log_df():
    """Return generation log as a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(
        'SELECT * FROM generation_log ORDER BY timestamp DESC', conn
    )
    conn.close()
    return df


def get_review_decisions_df():
    """Return all reviewer decisions as a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(
        'SELECT * FROM review_decisions ORDER BY timestamp DESC', conn
    )
    conn.close()
    return df


def get_review_queue_df():
    """Return comparison results that are not Pass and not yet Approved,
    joined with the latest reviewer decision (if any).
    """
    conn = get_connection()
    df = pd.read_sql_query(
        '''
        SELECT
            cr.comparison_id,
            cr.employee_id,
            cr.role,
            cr.overall_status,
            cr.coverage_score,
            cr.traceability_score,
            cr.flags_json,
            cr.timestamp,
            rd.reviewer_decision,
            rd.reviewer_notes
        FROM comparison_results cr
        LEFT JOIN (
            SELECT comparison_id, reviewer_decision, reviewer_notes
            FROM review_decisions
            WHERE decision_id IN (
                SELECT decision_id FROM review_decisions rd2
                ORDER BY timestamp DESC
            )
            GROUP BY comparison_id
        ) rd ON cr.comparison_id = rd.comparison_id
        WHERE cr.overall_status != 'Pass'
        ORDER BY cr.timestamp DESC
        ''',
        conn
    )
    conn.close()
    return df
