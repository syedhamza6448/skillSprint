# NimbusWorks Incident Response Standard Operating Procedure
Version: 1.0 | Effective: 2026-01-01

## 1. Incident Classification and Roles
### 1.1 Severity Level Matrix
Incidents are classified into Severity 1 (Critical Outage/Security Breach), Severity 2 (Major Service Degradation), and Severity 3 (Minor Defect).

### 1.2 Incident Commander
For Severity 1 incidents, a designated DevOps/IT Engineer serves as Incident Commander and assumes full control of technical response efforts.

## 2. Triage and Containment
### 2.1 Initial Assessment
Upon receiving an alert, the on-call DevOps/IT Engineer must triage the issue and establish a dedicated Incident Command Slack channel within 10 minutes.

### 2.2 Containment Actions
For security incidents, DevOps/IT Engineers must isolate compromised servers or revoke affected credentials within 15 minutes of triage.

## 3. Communication Protocols
### 3.1 Customer Advisory Updates
Software Support Engineers and Customer Support Executives must issue customer status updates every 30 minutes during Severity 1 outages.

### 3.2 Post-Incident Report (PIR)
Within 48 hours of resolving a Severity 1 incident, the Incident Commander must publish a Post-Incident Report (PIR) detailing root cause and preventative actions.

## 4. Continuous Improvement
### 4.1 Action Item Tracking
Action items identified in PIRs must be logged in project management tools and assigned to responsible teams with completion deadlines within 14 days.
