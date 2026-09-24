import os
import glob
import sqlite3
import uuid
import csv
import sys
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Ensure core modules can be imported
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from core.doc_processing import process_all
from core.db import get_connection, load_matrix, setup_db

def convert_to_docx(md_path, docx_path):
    doc = Document()
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('### '):
            doc.add_heading(line[4:], level=3)
        elif line.startswith('## '):
            doc.add_heading(line[3:], level=2)
        elif line.startswith('# '):
            doc.add_heading(line[2:], level=1)
        else:
            doc.add_paragraph(line)
    
    doc.save(docx_path)

def convert_to_pdf(md_path, pdf_path):
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 12))
            continue
        if line.startswith('### '):
            story.append(Paragraph(line[4:], styles['Heading3']))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], styles['Heading2']))
        elif line.startswith('# '):
            story.append(Paragraph(line[2:], styles['Heading1']))
        else:
            story.append(Paragraph(line, styles['Normal']))
            
    doc.build(story)

def convert_all_drafts():
    drafts_dir = 'data/company_docs_drafts'
    out_dir = 'data/company_docs'
    os.makedirs(out_dir, exist_ok=True)
    
    md_files = sorted(glob.glob(os.path.join(drafts_dir, '*.md')))
    
    for md_file in md_files:
        filename = os.path.basename(md_file)
        name, _ = os.path.splitext(filename)
        
        # 01..06 and 13..16 -> PDF, 07..12 and 17..20 -> DOCX
        doc_num = int(name.split('_')[0])
        if doc_num in [1, 2, 3, 4, 5, 6, 13, 14, 15, 16]:
            out_path = os.path.join(out_dir, name + '.pdf')
            convert_to_pdf(md_file, out_path)
            print(f"Converted to PDF: {out_path}")
        else:
            out_path = os.path.join(out_dir, name + '.docx')
            convert_to_docx(md_file, out_path)
            print(f"Converted to DOCX: {out_path}")

def get_doc_id(cursor, filename):
    cursor.execute("SELECT doc_id FROM documents WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    if row:
        return row[0]
    return f"MISSING_{filename}"

def build_matrix():
    conn = get_connection()
    cursor = conn.cursor()
    
    roles = [
        "Sales Executive", "Customer Support Executive", "HR Executive", 
        "Finance Associate", "Operations Coordinator", "Marketing Executive", 
        "Software Support Engineer", "Branch/Team Manager", "Data Analyst", 
        "DevOps/IT Engineer"
    ]
    
    rows = []
    
    # 1. Base mandatory requirements across all 10 roles from general docs (Docs 01, 04, 05)
    for role in roles:
        rows.append([str(uuid.uuid4()), role, "01_employee_handbook.pdf", "1.2 Our Values", "Embody transparency, innovation, accountability, and customer obsession.", "Y", "High", "Week1", "Culture", "Onboarding", "Values Quiz", "standard"])
        rows.append([str(uuid.uuid4()), role, "04_info_security_policy.pdf", "1.1 Passwords", "Use 14+ character passwords and change every 90 days.", "Y", "High", "Week1", "Security", "IT Setup", "Security Quiz", "standard"])
        rows.append([str(uuid.uuid4()), role, "05_workplace_conduct_policy.pdf", "2.1 Internal Communication", "Use Slack appropriately and observe response times.", "Y", "Medium", "Week1", "Communication", "Comms Setup", "Conduct Quiz", "standard"])

    # 2. Base mandatory requirements across all 10 roles from new general docs (Docs 13, 19, 20)
    for role in roles:
        rows.append([str(uuid.uuid4()), role, "13_it_equipment_policy.pdf", "3.1 Software Installation", "Install software only from the pre-approved company software repository.", "Y", "High", "Week1", "Security", "IT Setup", "Software Compliance", "standard"])

    # 3. Role-specific requirements from existing docs (Docs 01..12) - 3 per role
    role_specific_existing = {
        "Sales Executive": [
            ("07_sales_sop.docx", "1.1 Sourcing Leads", "Source leads via LinkedIn and marketing funnels.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("07_sales_sop.docx", "2.2 Proposal Creation", "Use standard pricing tiers and official templates.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("07_sales_sop.docx", "3.2 Handoff", "Complete the handoff form in CRM post-sale.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "Customer Support Executive": [
            ("08_customer_support_sop.docx", "1.1 Triage", "Monitor Zendesk and categorize tickets by severity.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("08_customer_support_sop.docx", "1.2 Response Times", "Acknowledge normal tickets within 4 hours.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("08_customer_support_sop.docx", "4.2 Customer Satisfaction (CSAT)", "Maintain an average CSAT of 4.5/5.0.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "HR Executive": [
            ("02_hr_policy.pdf", "1.1 Recruitment", "Use standardized assessment rubrics for hiring.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("02_hr_policy.pdf", "4.2 Offboarding", "Conduct exit interviews for departing employees.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("12_escalation_procedures.docx", "3.1 Workplace Conflict", "Mediate interpersonal conflicts.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "Finance Associate": [
            ("09_finance_sop.docx", "1.2 Salary Disbursal", "Process payroll on the 25th of every month.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("09_finance_sop.docx", "3.1 Invoice Generation", "Spot check 10% of generated invoices.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("09_finance_sop.docx", "4.1 Payment Terms", "Log vendor invoices and adhere to Net 30 terms.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "Operations Coordinator": [
            ("10_role_descriptions.docx", "3.2 Operations Coordinator", "Oversee daily administrative tasks.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("10_role_descriptions.docx", "3.2 Operations Coordinator", "Ensure office facilities operate smoothly.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("04_info_security_policy.pdf", "4.1 Badges", "Ensure all physical access uses ID badges.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "Marketing Executive": [
            ("10_role_descriptions.docx", "1.2 Marketing Executive", "Manage inbound marketing funnels.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("10_role_descriptions.docx", "1.2 Marketing Executive", "Track marketing ROI to support sales.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("07_sales_sop.docx", "1.1 Sourcing Leads", "Provide funnels for Sales Executives.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "Software Support Engineer": [
            ("08_customer_support_sop.docx", "2.2 Escalation", "Handle tickets escalated beyond 24 hours.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("12_escalation_procedures.docx", "1.1 Technical Issues", "Resolve bugs escalated by Customer Support.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("10_role_descriptions.docx", "2.2 Software Support Engineer", "Provide technical workarounds.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "Branch/Team Manager": [
            ("09_finance_sop.docx", "2.2 Approval Limits", "Approve expenses up to $500.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("03_leave_policy.pdf", "1.2 Approval Process", "Approve leave requests exceeding 3 days.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("10_role_descriptions.docx", "5.2 Branch/Team Manager", "Conduct performance reviews and set objectives.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "Data Analyst": [
            ("06_data_privacy_policy.pdf", "1.1 Customer Data", "Access data only relevant to reporting tasks.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("06_data_privacy_policy.pdf", "2.2 Data Anonymization", "Anonymize data for product analytics.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("10_role_descriptions.docx", "4.2 Data Analyst", "Create BI dashboards.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ],
        "DevOps/IT Engineer": [
            ("04_info_security_policy.pdf", "3.2 Response Protocol", "Isolate affected systems within 30 mins of a breach.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("06_data_privacy_policy.pdf", "3.2 Deletion Requests", "Process GDPR deletion requests within 14 days.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment"),
            ("12_escalation_procedures.docx", "2.2 System Outages", "Initiate Critical Incident Response within 15 minutes.", "Y", "High", "Week2", "Role Specific", "Task", "Assessment")
        ]
    }
    for role, reqs in role_specific_existing.items():
        for req in reqs:
            rows.append([str(uuid.uuid4()), role, req[0], req[1], req[2], req[3], req[4], req[5], req[6], req[7], req[8], "standard"])

    # 4. Role-specific requirements from new docs (Docs 13..20) - 3 per role
    role_specific_new = {
        "Sales Executive": [
            ("16_sales_code_of_conduct.pdf", "1.1 Truthful Representation", "Accurately represent SaaS platform features and pricing.", "Y", "High", "Week2", "Ethics", "Sales", "Compliance Quiz"),
            ("14_travel_expense_policy.pdf", "1.1 Travel Approval", "Obtain manager approval 14 days prior to business travel.", "Y", "Medium", "Week3", "Travel", "Expenses", "Travel Policy"),
            ("16_sales_code_of_conduct.pdf", "2.1 Respectful Communication", "Honor prospect cold call opt-out requests within 24 hours.", "Y", "High", "Week2", "Communication", "Outreach", "Sales SOP")
        ],
        "Customer Support Executive": [
            ("18_incident_response_sop.docx", "3.1 Customer Advisory Updates", "Issue customer status updates every 30 mins during Sev 1 outages.", "Y", "High", "Week3", "Incident Management", "Support", "Status Protocols"),
            ("20_remote_work_guidelines.docx", "1.2 Home Internet Requirements", "Maintain broadband connection with min 50 Mbps download speed.", "Y", "Medium", "Week1", "Remote Work", "Setup", "IT Guidelines"),
            ("19_diversity_inclusion_policy.docx", "2.1 Accommodations Policy", "Submit workplace accessibility accommodation requests to HR team.", "N", "Low", "Week2", "D&I", "HR", "Inclusion Guidelines")
        ],
        "HR Executive": [
            ("15_performance_review_sop.pdf", "1.1 Bi-Annual Review Schedule", "Manage bi-annual review calendar in June and December.", "Y", "High", "Week3", "Performance", "Reviews", "HR Operations"),
            ("19_diversity_inclusion_policy.docx", "1.2 Diverse Hiring Practices", "Ensure job descriptions use inclusive language and diverse shortlists.", "Y", "High", "Week2", "D&I", "Recruitment", "Hiring Rubrics"),
            ("15_performance_review_sop.pdf", "4.1 Performance Improvement Plan (PIP)", "Co-develop 60-day PIP for employees with unsatisfactory ratings.", "Y", "High", "Month1", "Performance", "Discipline", "PIP SOP")
        ],
        "Finance Associate": [
            ("14_travel_expense_policy.pdf", "4.1 Submission Timeline", "Process travel expense reports submitted within 15 days of travel.", "Y", "High", "Week2", "Finance", "Reimbursements", "Expense SOP"),
            ("17_data_retention_policy.docx", "2.1 Financial and Tax Records", "Retain client invoices and financial records for a minimum of 7 years.", "Y", "High", "Month1", "Compliance", "Record Keeping", "Tax Compliance"),
            ("14_travel_expense_policy.pdf", "2.1 Meal Per Diem", "Enforce meal per diem limit of $75 per day with itemized receipts.", "Y", "Medium", "Week2", "Finance", "Audit", "Per Diem Policy")
        ],
        "Operations Coordinator": [
            ("14_travel_expense_policy.pdf", "1.2 Booking Channels", "Book flights and lodging through official company travel portal.", "Y", "High", "Week2", "Operations", "Travel Management", "Portal SOP"),
            ("20_remote_work_guidelines.docx", "4.1 Return Shipping Protocols", "Provide pre-paid shipping labels to remote employees returning equipment.", "Y", "Medium", "Week3", "Logistics", "Offboarding", "Asset Return"),
            ("19_diversity_inclusion_policy.docx", "2.2 Inclusive Facilities", "Ensure office facilities meet accessibility guidelines.", "Y", "High", "Month1", "Facilities", "D&I", "Building Standards")
        ],
        "Marketing Executive": [
            ("16_sales_code_of_conduct.pdf", "2.2 Competitive Statements", "Avoid defamatory or unsubstantiated claims about competitors.", "Y", "High", "Week2", "Marketing Ethics", "Content", "Brand Standards"),
            ("19_diversity_inclusion_policy.docx", "3.2 Meeting Participation", "Participate in approved inclusion workshops up to 2 hours per month.", "N", "Low", "Month1", "D&I", "Culture", "Workshop Participation"),
            ("14_travel_expense_policy.pdf", "1.1 Travel Approval", "Pre-approve marketing event travel with Branch/Team Manager.", "Y", "Medium", "Week3", "Travel", "Events", "Budget Approval")
        ],
        "Software Support Engineer": [
            ("18_incident_response_sop.docx", "3.1 Customer Advisory Updates", "Collaborate on customer status updates during Sev 1 outages.", "Y", "High", "Week2", "Incident Response", "Support", "Outage SOP"),
            ("13_it_equipment_policy.pdf", "2.2 Repairs and Replacements", "Report hardware malfunctions to IT within 24 hours.", "Y", "Medium", "Week1", "IT Support", "Hardware", "Equipment Policy"),
            ("20_remote_work_guidelines.docx", "3.1 Device Physical Security", "Set screen locks to activate after 5 minutes of inactivity.", "Y", "High", "Week1", "Security", "Remote Safety", "Device Protocol")
        ],
        "Branch/Team Manager": [
            ("14_travel_expense_policy.pdf", "1.1 Travel Approval", "Pre-approve team business travel requests 14 days in advance.", "Y", "High", "Week2", "Management", "Approvals", "Travel Governance"),
            ("15_performance_review_sop.pdf", "1.2 Goal Setting (OKRs)", "Approve team member OKRs within first 2 weeks of each cycle.", "Y", "High", "Week2", "Performance", "OKRs", "Management SOP"),
            ("16_sales_code_of_conduct.pdf", "3.1 Lead Ownership Rules", "Reassign sales leads uncontacted after 30 days.", "Y", "Medium", "Month1", "Sales Operations", "Lead Allocation", "CRM Rules")
        ],
        "Data Analyst": [
            ("17_data_retention_policy.docx", "1.2 Compliance Standards", "Ensure analytics data handling complies with GDPR and CCPA.", "Y", "High", "Week2", "Data Governance", "Analytics", "Privacy SOP"),
            ("13_it_equipment_policy.pdf", "1.2 Asset Tagging", "Ensure allocated IT hardware retains physical asset tags.", "N", "Low", "Week1", "Asset Management", "IT", "Policy Check"),
            ("20_remote_work_guidelines.docx", "3.2 Home Network Security", "Secure remote Wi-Fi network with WPA3 encryption when working remotely.", "Y", "High", "Week1", "Security", "Remote Work", "Network Security")
        ],
        "DevOps/IT Engineer": [
            ("13_it_equipment_policy.pdf", "1.1 Standard Issue", "Oversee hardware allocation and provisioning for new hires.", "Y", "High", "Week1", "IT Operations", "Provisioning", "Equipment SOP"),
            ("17_data_retention_policy.docx", "2.2 System and Audit Logs", "Maintain network security and audit logs for at least 365 days.", "Y", "High", "Week2", "Security Logs", "Audit", "Log Retention"),
            ("18_incident_response_sop.docx", "1.2 Incident Commander", "Act as Incident Commander for Severity 1 incidents.", "Y", "High", "Week2", "Incident Command", "Ops", "Severity SOP")
        ]
    }
    for role, reqs in role_specific_new.items():
        for req in reqs:
            rows.append([str(uuid.uuid4()), role, req[0], req[1], req[2], req[3], req[4], req[5], req[6], req[7], req[8], "standard"])

    # 5. Additional real requirements pulled from original docs (01..12) - 20 rows
    additional_existing = [
        ("Sales Executive", "05_workplace_conduct_policy.pdf", "1.2 Dress Code", "Wear business attire when meeting clients.", "Y", "Medium", "Week1", "Conduct", "Client Meeting", "Dress Code Policy"),
        ("Customer Support Executive", "08_customer_support_sop.docx", "3.2 Status Updates", "Provide customer status updates at least every 48 hours for ongoing issues.", "Y", "High", "Week2", "Communication", "Ticket Management", "Support Communication"),
        ("HR Executive", "02_hr_policy.pdf", "2.2 Health Benefits", "Enroll full-time employees in health insurance after 90-day probation.", "Y", "Medium", "Month1", "Benefits", "HR Operations", "Health Insurance"),
        ("Finance Associate", "09_finance_sop.docx", "1.1 Timesheets", "Ensure hourly employee timesheets are approved by the 18th.", "Y", "High", "Week3", "Payroll", "Timesheet Audit", "Payroll SOP"),
        ("Operations Coordinator", "01_employee_handbook.pdf", "3.1 Office Safety", "Follow safety protocols and report suspicious hazards immediately.", "Y", "High", "Week1", "Safety", "Facility Ops", "Safety Quiz"),
        ("Marketing Executive", "05_workplace_conduct_policy.pdf", "2.2 Social Media", "Do not disclose confidential company info on personal social media.", "Y", "High", "Week1", "Compliance", "Public Relations", "Social Media Policy"),
        ("Software Support Engineer", "08_customer_support_sop.docx", "2.1 First-Contact Resolution", "Utilize internal knowledge base for troubleshooting before escalating.", "Y", "Medium", "Week2", "Troubleshooting", "Knowledge Base", "Support SOP"),
        ("Branch/Team Manager", "05_workplace_conduct_policy.pdf", "3.2 Gifts and Entertainment", "Approve or decline client gifts exceeding $50 in value.", "Y", "Medium", "Month1", "Governance", "Ethics", "Gift Approval"),
        ("Data Analyst", "06_data_privacy_policy.pdf", "2.1 Permitted Use", "Ensure customer data is not used for marketing without explicit consent.", "Y", "High", "Week2", "Privacy", "Data Usage", "Consent Policy"),
        ("DevOps/IT Engineer", "04_info_security_policy.pdf", "2.1 Encryption", "Enable full-disk encryption on all company laptops.", "Y", "High", "Week1", "Security", "Endpoint Protection", "Encryption Policy"),
        ("Sales Executive", "07_sales_sop.docx", "1.2 Qualification", "Qualify leads using BANT framework before adding to CRM.", "Y", "High", "Week2", "Sales", "Lead Qualification", "BANT Quiz"),
        ("Customer Support Executive", "08_customer_support_sop.docx", "3.1 Tone and Empathy", "Maintain polite, empathetic tone and avoid technical jargon.", "Y", "Medium", "Week1", "Communication", "Customer Relations", "Tone Guide"),
        ("HR Executive", "02_hr_policy.pdf", "4.1 Resignation", "Receive 2-week resignation notice and notify managers.", "Y", "High", "Month1", "Offboarding", "Resignation SOP", "Exit Process"),
        ("Finance Associate", "09_finance_sop.docx", "3.2 Outstanding Payments", "Suspend account access for client invoices overdue by 60 days.", "Y", "High", "Month1", "Collections", "Account Management", "Dunning SOP"),
        ("Operations Coordinator", "01_employee_handbook.pdf", "2.2 Remote Work", "Process remote work requests up to 3 days per week.", "N", "Low", "Week2", "Administration", "Remote Policy", "Workplace Ops"),
        ("Marketing Executive", "01_employee_handbook.pdf", "4.2 Professional Development", "Utilize $1,000 annual stipend for relevant courses and certifications.", "N", "Low", "Month1", "Professional Growth", "Training", "Stipend Guidelines"),
        ("Software Support Engineer", "11_faqs.docx", "3.2 Who do I contact for IT support?", "Respond to hardware/software tickets in designated IT Slack channel.", "Y", "Medium", "Week1", "IT Support", "Communication", "Slack SOP"),
        ("Branch/Team Manager", "01_employee_handbook.pdf", "4.1 Performance Reviews", "Evaluate employee performance against set OKRs bi-annually.", "Y", "High", "Month1", "Management", "Reviews", "OKR Guidelines"),
        ("Data Analyst", "06_data_privacy_policy.pdf", "1.1 Customer Data", "Limit access to customer data solely to reporting tasks.", "Y", "High", "Week2", "Privacy", "Access Control", "Data Policy"),
        ("DevOps/IT Engineer", "04_info_security_policy.pdf", "1.2 Multi-Factor Authentication (MFA)", "Enforce mandatory MFA across all internal systems.", "Y", "High", "Week1", "Security", "MFA Setup", "Access Policy")
    ]
    for item in additional_existing:
        rows.append([str(uuid.uuid4()), item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], item[9], "standard"])

    # 6. 10 Conflicting/Ambiguous requirement pairs (20 rows total across dataset)
    conflicts = [
        ("Sales Executive", "01_employee_handbook.pdf", "2.1 Working Hours", "Core hours are 10 AM to 3 PM.", "11_faqs.docx", "1.1 What are our core working hours?", "Core hours are 9 AM to 5 PM strictly."),
        ("Branch/Team Manager", "03_leave_policy.pdf", "1.2 Approval Process", "Managers must approve leaves over 3 days.", "03_leave_policy.pdf", "4.1 Extended Absences", "Only HR can approve leaves over 3 days."),
        ("Finance Associate", "09_finance_sop.docx", "2.2 Approval Limits", "Managers can approve expenses up to $500.", "09_finance_sop.docx", "2.2 Approval Limits", "All expenses require Finance Director approval."),
        ("DevOps/IT Engineer", "06_data_privacy_policy.pdf", "3.1 Retention Period", "Retain customer data for 90 days after subscription ends.", "06_data_privacy_policy.pdf", "3.2 Deletion Requests", "Delete all customer data immediately upon subscription end."),
        ("HR Executive", "02_hr_policy.pdf", "3.1 Progressive Discipline", "Must follow progressive steps before termination.", "02_hr_policy.pdf", "3.2 Immediate Dismissal", "Managers can terminate immediately for any violation."),
        ("HR Executive", "02_hr_policy.pdf", "4.1 Resignation", "Employees must provide a minimum 2-week notice period when resigning.", "10_role_descriptions.docx", "3.1 HR Executive", "Senior staff must provide a minimum 4-week notice period prior to resignation."),
        ("Finance Associate", "09_finance_sop.docx", "2.1 Submitting Claims", "Expense claims must be submitted within 30 days of transaction.", "14_travel_expense_policy.pdf", "4.1 Submission Timeline", "Travel expense reports must be submitted within 15 days of returning."),
        ("Customer Support Executive", "08_customer_support_sop.docx", "1.2 Response Times", "Acknowledge normal tickets within 4 hours during business hours.", "11_faqs.docx", "1.1 What are our core working hours?", "Acknowledge non-critical tickets within 2 business days."),
        ("DevOps/IT Engineer", "04_info_security_policy.pdf", "1.1 Passwords", "Passwords must be changed every 90 days.", "13_it_equipment_policy.pdf", "2.1 Hardware Maintenance", "Passwords must be updated every 180 days per IT rotation schedule."),
        ("Branch/Team Manager", "01_employee_handbook.pdf", "2.2 Remote Work", "Employees are permitted to work remotely up to 3 days a week.", "20_remote_work_guidelines.docx", "1.1 Ergonomic Workspace", "Full-time remote work is permitted for all employees after 30 days.")
    ]
    for c in conflicts:
        rows.append([str(uuid.uuid4()), c[0], c[1], c[2], c[3], "Y", "Medium", "Month1", "Conflict", "Task", "Topic", "conflicting"])
        rows.append([str(uuid.uuid4()), c[0], c[4], c[5], c[6], "Y", "Medium", "Month1", "Conflict", "Task", "Topic", "conflicting"])

    # 7. 10 Policy-version change pairs (20 rows total across dataset: 10 superseded + 10 current)
    outdated = [
        ("Sales Executive", "07_sales_sop.docx", "2.2 Proposal Creation", "[v0.9] Use old pricing tiers.", "[v1.0] Use standard pricing tiers."),
        ("Customer Support Executive", "08_customer_support_sop.docx", "1.2 Response Times", "[v0.9] Acknowledge tickets within 24 hours.", "[v1.0] Acknowledge tickets within 4 hours."),
        ("Finance Associate", "09_finance_sop.docx", "4.1 Payment Terms", "[v0.9] Net 60 terms for vendors.", "[v1.0] Net 30 terms for vendors."),
        ("Data Analyst", "06_data_privacy_policy.pdf", "3.1 Retention Period", "[v0.9] Retain data indefinitely.", "[v1.0] Retain data for 90 days."),
        ("Marketing Executive", "10_role_descriptions.docx", "1.2 Marketing Executive", "[v0.9] Manage outbound cold calls.", "[v1.0] Manage inbound marketing funnels."),
        ("HR Executive", "15_performance_review_sop.pdf", "1.1 Bi-Annual Review Schedule", "[v0.9] Annual performance reviews held only in December.", "[v1.0] Bi-annual performance reviews held in June and December."),
        ("Finance Associate", "14_travel_expense_policy.pdf", "2.1 Meal Per Diem", "[v0.9] Daily meal per diem limit of $50.", "[v1.0] Daily meal per diem limit of $75."),
        ("DevOps/IT Engineer", "17_data_retention_policy.docx", "2.2 System and Audit Logs", "[v0.9] Maintain audit logs for 90 days.", "[v1.0] Maintain audit logs for at least 365 days."),
        ("Branch/Team Manager", "15_performance_review_sop.pdf", "4.1 Performance Improvement Plan (PIP)", "[v0.9] Standard PIP duration is 30 days.", "[v1.0] Standard PIP duration is 60 days."),
        ("Operations Coordinator", "20_remote_work_guidelines.docx", "2.1 Work-From-Home Stipend", "[v0.9] Work-from-home setup stipend of $250.", "[v1.0] Work-from-home setup stipend of $500.")
    ]
    for o in outdated:
        rows.append([str(uuid.uuid4()), o[0], o[1], o[2], o[3], "N", "Low", "Week1", "Outdated", "Task", "Topic", "policy_version_old"])
        rows.append([str(uuid.uuid4()), o[0], o[1], o[2], o[4], "Y", "High", "Week1", "Current", "Task", "Topic", "policy_version_new"])

    # Map filenames to real doc_ids from the SQLite database
    for row in rows:
        filename = row[2]
        doc_id = get_doc_id(cursor, filename)
        row[2] = doc_id

    # Write expanded matrix CSV
    os.makedirs('data', exist_ok=True)
    csv_path = 'data/role_requirement_matrix.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "requirement_id", "role", "policy_source_doc", "source_section", 
            "requirement_text", "mandatory", "priority", "due_stage", 
            "competency_area", "related_task", "related_assessment_topic", "case_type",
            "prerequisite_requirement_id"
        ])
        writer.writerows(rows)
        
    print(f"Generated {csv_path} with {len(rows)} rows.")
    conn.close()

def verify_dataset():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM requirement_matrix")
    req_count = cursor.fetchone()[0]
    
    # Check invalid citations
    cursor.execute("""
        SELECT rm.requirement_id, rm.policy_source_doc, rm.source_section
        FROM requirement_matrix rm
        LEFT JOIN chunks c ON rm.policy_source_doc = c.doc_id AND rm.source_section = c.heading
        WHERE c.chunk_id IS NULL
    """)
    invalid_citations = cursor.fetchall()
    
    # Count mandatory vs non-mandatory
    cursor.execute("SELECT mandatory, COUNT(*) FROM requirement_matrix GROUP BY mandatory")
    mandatory_counts = dict(cursor.fetchall())
    
    # Count case types
    cursor.execute("SELECT competency_area, COUNT(*) FROM requirement_matrix GROUP BY competency_area")
    comp_counts = dict(cursor.fetchall())

    conn.close()
    
    print("=== DATASET VERIFICATION SUMMARY ===")
    print(f"Total Documents in DB: {doc_count}")
    print(f"Total Chunks in DB: {chunk_count}")
    print(f"Total Requirements in Matrix: {req_count}")
    print(f"Mandatory Counts: {mandatory_counts}")
    print(f"Competency Area Breakdown: {comp_counts}")
    print(f"Invalid Citations Count: {len(invalid_citations)}")
    
    if len(invalid_citations) > 0:
        print(f"WARNING: Found {len(invalid_citations)} invalid citations!")
        for inv in invalid_citations[:5]:
            print(f"  Req ID: {inv[0]} -> Doc ID: {inv[1]}, Section: {inv[2]}")
    else:
        print("SUCCESS: 100% of matrix requirements cite real, existing database chunks!")

def main():
    print("--- 1. Converting Drafts to PDF and DOCX ---")
    convert_all_drafts()
    
    print("\n--- 2. Parsing and Chunking Documents into SQLite ---")
    process_all('data/company_docs')
    
    print("\n--- 3. Generating Expanded Matrix CSV ---")
    build_matrix()
    
    print("\n--- 4. Loading Matrix into SQLite ---")
    load_matrix('data/role_requirement_matrix.csv')
    
    print("\n--- 5. Verifying Expanded Dataset ---")
    verify_dataset()

if __name__ == '__main__':
    main()
