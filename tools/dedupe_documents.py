import os
import sys
import sqlite3
import pandas as pd

# Ensure parent directory is in sys.path to access core package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.db import DB_PATH


def dedupe_documents():
    csv_path = os.path.join(project_root, "data", "role_requirement_matrix.csv")

    # 1. Read matrix CSV to identify referenced document IDs and matrix row IDs
    doc_id_to_matrix_rows = {}
    if os.path.exists(csv_path):
        df_matrix = pd.read_csv(csv_path)

        col_name = None
        if "policy_source_doc" in df_matrix.columns:
            col_name = "policy_source_doc"
        elif "source_document_id" in df_matrix.columns:
            col_name = "source_document_id"

        if col_name:
            for idx, row in df_matrix.iterrows():
                doc_id = str(row[col_name]).strip() if pd.notna(row[col_name]) else ""
                req_id = (
                    str(row["requirement_id"]).strip()
                    if "requirement_id" in df_matrix.columns and pd.notna(row["requirement_id"])
                    else f"Row {idx+1}"
                )
                if doc_id:
                    doc_id_to_matrix_rows.setdefault(doc_id, []).append(req_id)
    else:
        print(f"Warning: Matrix CSV not found at {csv_path}. Proceeding with 0 matrix references.")

    referenced_doc_ids = set(doc_id_to_matrix_rows.keys())

    # 2. Query documents table from database
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT doc_id, filename, file_type, version, effective_date, upload_date, file_hash FROM documents"
    )
    rows = cursor.fetchall()
    doc_count_before = len(rows)

    # 3. Group documents by filename
    filename_to_docs = {}
    for row in rows:
        doc_id, filename, file_type, version, effective_date, upload_date, file_hash = row
        doc_info = {
            "doc_id": doc_id,
            "filename": filename,
            "file_type": file_type,
            "version": version,
            "effective_date": effective_date,
            "upload_date": upload_date,
            "file_hash": file_hash,
        }
        filename_to_docs.setdefault(filename, []).append(doc_info)

    conflicts = []
    docs_to_delete = []

    # 4. Process duplicate filename groups according to safety rules
    for filename, docs in filename_to_docs.items():
        if len(docs) <= 1:
            continue

        referenced_in_group = [d for d in docs if d["doc_id"] in referenced_doc_ids]

        if len(referenced_in_group) > 1:
            # Conflict: More than one doc_id referenced by matrix for the same filename
            conflicts.append(
                {
                    "filename": filename,
                    "conflicting_docs": [
                        {
                            "doc_id": d["doc_id"],
                            "matrix_req_ids": doc_id_to_matrix_rows.get(d["doc_id"], []),
                            "upload_date": d["upload_date"],
                        }
                        for d in referenced_in_group
                    ],
                }
            )
        elif len(referenced_in_group) == 1:
            # Safe case: Exactly one doc_id referenced by matrix -> keep it, delete unreferenced
            doc_to_keep = referenced_in_group[0]
            docs_to_delete.extend([d for d in docs if d["doc_id"] != doc_to_keep["doc_id"]])
        else:
            # Safe case: None referenced by matrix -> keep most recent upload_date
            sorted_docs = sorted(
                docs,
                key=lambda d: (str(d["upload_date"] or ""), d["doc_id"]),
                reverse=True,
            )
            doc_to_keep = sorted_docs[0]
            docs_to_delete.extend([d for d in docs if d["doc_id"] != doc_to_keep["doc_id"]])

    # 5. Conflict Check: Stop execution if any conflicts were detected
    if conflicts:
        print("\n" + "=" * 80)
        print("⚠️ WARNING: CONFLICTS DETECTED — STOPPING CLEANUP TO PREVENT DATA LOSS")
        print("=" * 80)
        for c in conflicts:
            print(
                f"\nFilename: '{c['filename']}' has {len(c['conflicting_docs'])} conflicting doc_ids referenced by matrix:"
            )
            for cd in c["conflicting_docs"]:
                reqs_str = (
                    ", ".join(cd["matrix_req_ids"])
                    if len(cd["matrix_req_ids"]) <= 10
                    else ", ".join(cd["matrix_req_ids"][:10]) + "..."
                )
                print(f"  - doc_id: {cd['doc_id']} (uploaded: {cd['upload_date']})")
                print(f"    Referenced by {len(cd['matrix_req_ids'])} matrix row(s): {reqs_str}")
        print("\nNo database deletions were performed.")
        print("Please review and resolve matrix references manually before re-running deduplication.\n")

        print("=" * 80)
        print("CLEANUP SUMMARY")
        print("=" * 80)
        print(f"Documents before cleanup:   {doc_count_before}")
        print(f"Documents after cleanup:    {doc_count_before} (Aborted due to conflicts)")
        print(f"Chunks deleted:             0")
        print(f"Conflicts requiring review: {len(conflicts)}")
        print("=" * 80)
        conn.close()
        return

    # 6. Perform deletions safely if no conflicts exist
    doc_ids_to_delete = [d["doc_id"] for d in docs_to_delete]
    chunks_deleted_count = 0

    if doc_ids_to_delete:
        placeholders = ",".join(["?"] * len(doc_ids_to_delete))

        cursor.execute(
            f"SELECT COUNT(*) FROM chunks WHERE doc_id IN ({placeholders})",
            doc_ids_to_delete,
        )
        chunks_deleted_count = cursor.fetchone()[0]

        cursor.execute(
            f"DELETE FROM chunks WHERE doc_id IN ({placeholders})",
            doc_ids_to_delete,
        )

        cursor.execute(
            f"DELETE FROM documents WHERE doc_id IN ({placeholders})",
            doc_ids_to_delete,
        )

        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count_after = cursor.fetchone()[0]
    conn.close()

    print("\n" + "=" * 80)
    print("SUCCESS: DEDUPLICATION CLEANUP COMPLETED")
    print("=" * 80)
    print(f"Documents before cleanup:   {doc_count_before}")
    print(f"Documents after cleanup:    {doc_count_after}")
    print(f"Duplicates removed:         {len(doc_ids_to_delete)}")
    print(f"Chunks deleted:             {chunks_deleted_count}")
    print(f"Conflicts requiring review: 0")
    print("=" * 80)


if __name__ == "__main__":
    dedupe_documents()
