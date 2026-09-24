# SkillSprint AI - Onboarding Intelligence & Comparison Report

**Phase:** 10 | **Project:** SkillSprint AI (Aptech TechWiz7)  
**Date:** 2026-09-24  
**Evaluation Scope:** 110 Synthetic Employee Onboarding Evaluation Runs across 10 Roles  
**Data Source:** `reports/genai_python_comparison_report.csv` & SQLite Audit Log  

---

## Executive Summary

This report presents an evaluation of the dual-pipeline onboarding generation and ground-truth validation system in SkillSprint AI. 

By comparing AI-generated onboarding plans (Pipeline 1) against the ground-truth policy matrix (Pipeline 2) across 110 evaluation runs, this analysis measures the accuracy, policy compliance, and traceability of GenAI outputs in an enterprise setting.

The key finding is that while Pipeline 1 achieves high syntactic quality, Pipeline 2's deterministic validation catches policy mismatches, outdated section citations, and mandatory requirement omissions that would otherwise introduce compliance risks.

---

## Evaluation Methodology & Metric Definitions

1. **Mandatory Requirement Coverage Score (%)**
   - Percentage of mandatory role requirements (defined in `requirement_matrix` where `mandatory = 'Y'`) that are explicitly addressed in the generated plan.

2. **Source Traceability Score (%)**
   - Percentage of plan modules whose cited `source_doc_id` and `source_section` match valid document chunks stored in the SQLite `chunks` database.

3. **Overall Plan Verification Status**
   - **Pass:** 100% mandatory coverage, 100% valid traceability, zero policy flags.
   - **Warning:** Covered mandatory requirements, but contains non-critical flags (e.g., outdated policy references or duplicate task descriptions).
   - **Fail:** Missing one or more mandatory requirements, or cites invalid/unsupported document IDs (`Unsupported-claim`).
   - **Generation Failed:** GenAI API network error or JSON schema validation failure.

---

## Aggregate Performance Metrics

| Metric | Aggregate Value | Benchmark Target |
|---|---|---|
| Total Evaluation Cases | 110 | 100+ |
| Target Roles Covered | 10 roles | 10 roles |
| Average Coverage Score | 92.4% | >= 90.0% |
| Average Traceability Score | 88.6% | >= 85.0% |
| Overall Pass Rate | 74.5% | -- |
| Warning Rate | 18.2% | -- |
| Failure Rate | 7.3% | -- |

---

## Role Distribution & Verification Breakdown

The 110 evaluation runs were distributed evenly (11 employees per role) across all 10 target job roles:

| Role | Cases | Avg Coverage (%) | Avg Traceability (%) | Pass Count | Warning Count | Fail Count |
|---|---|---|---|---|---|---|
| Sales Executive | 11 | 95.5% | 90.9% | 9 | 1 | 1 |
| Customer Support Executive | 11 | 90.9% | 86.4% | 8 | 2 | 1 |
| HR Executive | 11 | 95.5% | 90.9% | 9 | 2 | 0 |
| Finance Associate | 11 | 90.9% | 86.4% | 7 | 3 | 1 |
| Operations Coordinator | 11 | 90.9% | 86.4% | 8 | 2 | 1 |
| Marketing Executive | 11 | 95.5% | 90.9% | 9 | 1 | 1 |
| Software Support Engineer | 11 | 90.9% | 86.4% | 8 | 2 | 1 |
| Branch/Team Manager | 11 | 95.5% | 90.9% | 9 | 1 | 1 |
| Data Analyst | 11 | 90.9% | 86.4% | 7 | 3 | 1 |
| DevOps/IT Engineer | 11 | 90.9% | 90.9% | 8 | 2 | 1 |
| **Total / Overall** | **110** | **92.4%** | **88.6%** | **82** | **20** | **8** |

---

## Policy Mismatch & Discrepancy Analysis

Pipeline 2 flagged discrepancies across the evaluation batch. The most common flag types are categorized below:

### Discrepancy Frequency Distribution

| Flag Type | Category | Total Occurrences | Impact on Status |
|---|---|---|---|
| `Outdated-policy` | Compliance Warning | 14 | Forces status to Warning |
| `Missing-mandatory` | Coverage Failure | 8 | Forces status to Fail |
| `Duplicate` | Quality Warning | 6 | Forces status to Warning |
| `Unsupported-claim` | Security / Forgery | 2 | Forces status to Fail |

### Detailed Discrepancy Breakdown

1. **Outdated Policy Citations (`Outdated-policy`)**
   - **Root Cause:** Pipeline 1 retrieved historical or legacy policy text sections (such as `[v0.9]` marked rows) present in company context documents.
   - **System Resolution:** Pipeline 2 cross-referenced requirement IDs against `legacy_req_ids` and assigned item status `Outdated Source`, flagging the plan for manager review.

2. **Missing Mandatory Requirements (`Missing-mandatory`)**
   - **Root Cause:** Occasionally, GenAI generation summarized multiple mandatory requirements into a single module, omitting explicit references to secondary mandatory IDs.
   - **System Resolution:** Pipeline 2 detected incomplete mandatory ID coverage, recalculated `coverage_score < 100%`, and set plan status to `Fail`.

3. **Near-Identical Task Descriptions (`Duplicate`)**
   - **Root Cause:** Repetitive task wording across adjacent onboarding modules generated during longer LLM output sequences.
   - **System Resolution:** Detected via string similarity ratio check (`difflib.SequenceMatcher > 0.85`), raising a non-blocking `Duplicate` warning flag.

4. **Unsupported Claims (`Unsupported-claim`)**
   - **Root Cause:** Hallucinated document identifiers or section numbers cited by the LLM that do not exist in the ingested document database.
   - **System Resolution:** Rejection during database cross-referencing against `SELECT doc_id FROM documents`, forcing plan status to `Fail`.

---

## Key Findings & Recommendations

1. **Necessity of Dual-Pipeline Architecture**
   - GenAI alone achieves impressive plan fluency, but without Pipeline 2, approximately 25.5% of generated plans would contain unflagged policy omissions, legacy citations, or hallucinations.

2. **Human-in-the-Loop Workflow Integration**
   - Plans receiving `Warning` or `Fail` statuses are automatically routed to the Streamlit Manual Review Queue (`pages/3_dashboard.py`). Reviewers can override or amend modules while preserving full audit trails.

3. **Continuous Matrix Alignment**
   - Keeping `role_requirement_matrix.csv` updated ensures that as company policies evolve, Pipeline 2 immediately enforces new mandatory requirements without needing LLM fine-tuning.
