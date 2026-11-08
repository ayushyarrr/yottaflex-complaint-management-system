# Anomaly Scenarios and Ground Truth

## 1. Purpose

This document describes six deliberately constructed anomaly scenarios for the YottaFlex Complaint Management System.

The scenarios represent data-integrity, workflow, SLA, recurrence and routing problems that may occur in a complaint-management operation.

Each scenario has:
- A unique anomaly identifier.
- An issue type.
- An affected entity.
- A description of the problem.
- Test data representing the scenario.
- An expected detection description.
- A ground-truth label.

The anomaly fixtures are stored separately from the valid synthetic dataset.

## 2. Anomaly Dataset Design

The project maintains two separate data resources:

| Resource | Purpose |
|---|---|
| `data/generated/full/` | Valid synthetic operational dataset |
| `data/anomalies/anomaly_cases.json` | Deliberately constructed anomaly scenarios |
| `data/ground_truth/anomaly_ground_truth.csv` | Ground-truth labels and expected detection descriptions |

This separation prevents deliberately invalid test records from corrupting the valid operational database.

The ground-truth file provides reference labels for future or separate anomaly-detection evaluation.

**Important:** These fixtures define expected anomaly cases. They do not, by themselves, demonstrate that an automated anomaly-detection engine has detected or classified them.

## 3. Defined Anomaly Scenarios

### ANOM-001 — Complaint Without Customer

- **Issue type:** `COMPLAINT_WITHOUT_CUSTOMER`
- **Affected entity:** Complaint
- **Severity:** CRITICAL
- **Ground truth:** ANOMALY

**Scenario**

A complaint record references a customer identifier that does not exist in the Customer master table.

**Expected detection**

The complaint violates the required customer relationship. A foreign-key integrity check should identify the missing customer reference.

**Business impact**

The system cannot reliably identify the customer associated with the complaint. Customer communication, order history and complaint ownership may become unreliable.

### ANOM-002 — Resolution Before Complaint Creation

- **Issue type:** `RESOLUTION_BEFORE_COMPLAINT`
- **Affected entity:** Resolution
- **Severity:** CRITICAL
- **Ground truth:** ANOMALY

**Scenario**

A resolution timestamp occurs earlier than the creation timestamp of its associated complaint.

**Expected detection**

A chronology validation should identify that the resolution occurred before the complaint existed.

**Business impact**

The record represents an impossible workflow sequence and makes resolution-time metrics unreliable.

### ANOM-003 — Incorrect SLA Pause

- **Issue type:** `INCORRECT_SLA_PAUSE`
- **Affected entity:** SLAClock
- **Severity:** HIGH
- **Ground truth:** ANOMALY

**Scenario**

The SLA clock records a pause, but the recorded paused duration and resolution deadline extension are inconsistent.

The fixture represents a one-hour pause with zero recorded paused seconds and no corresponding deadline extension.

**Expected detection**

An SLA consistency check should compare the pause interval, accumulated paused seconds and adjusted resolution deadline.

**Business impact**

Incorrect pause accounting can produce misleading SLA breach results and inaccurate operational performance metrics.

### ANOM-004 — Repeat Issue Not Linked

- **Issue type:** `REPEAT_ISSUE_NOT_LINKED`
- **Affected entity:** Complaint
- **Severity:** MEDIUM
- **Ground truth:** ANOMALY

**Scenario**

A customer submits a complaint concerning a previously reported issue, but the repeat relationship is not reflected correctly.

The recurrence count and repeat-complaint relationship are inconsistent.

**Expected detection**

A recurrence validation should identify the missing relationship or incorrect recurrence count.

**Business impact**

Repeated customer problems may be treated as unrelated first-time complaints. This can result in under-prioritization and incomplete customer history.

### ANOM-005 — Critical Safety Complaint Assigned to the Wrong Team

- **Issue type:** `CRITICAL_SAFETY_LOW_PRIORITY_ASSIGNMENT`
- **Affected entity:** Assignment
- **Severity:** CRITICAL
- **Ground truth:** ANOMALY

**Scenario**

A critical product-safety complaint is assigned to General Support instead of Safety Response.

**Expected detection**

A routing validation should compare the complaint's safety classification and priority against its assigned team.

**Business impact**

A safety-related complaint may not receive the specialized attention required by the business rules.

The expected routing for product-safety complaints is Safety Response, with P1 priority enforced by the safety override.

### ANOM-006 — Survey Submitted Before Closure

- **Issue type:** `SURVEY_BEFORE_CLOSURE`
- **Affected entity:** Survey
- **Severity:** HIGH
- **Ground truth:** ANOMALY

**Scenario**

A customer satisfaction survey is submitted before the associated complaint reaches CLOSED status.

**Expected detection**

A lifecycle chronology check should compare the survey submission timestamp with the complaint closure event.

**Business impact**

Customer satisfaction data may be collected before the complaint outcome is finalized, making the feedback premature or misleading.

## 4. Ground-Truth Reference

The file `data/ground_truth/anomaly_ground_truth.csv` contains the reference labels.

| Anomaly ID | Issue type | Ground-truth label |
|---|---|---|
| ANOM-001 | COMPLAINT_WITHOUT_CUSTOMER | ANOMALY |
| ANOM-002 | RESOLUTION_BEFORE_COMPLAINT | ANOMALY |
| ANOM-003 | INCORRECT_SLA_PAUSE | ANOMALY |
| ANOM-004 | REPEAT_ISSUE_NOT_LINKED | ANOMALY |
| ANOM-005 | CRITICAL_SAFETY_LOW_PRIORITY_ASSIGNMENT | ANOMALY |
| ANOM-006 | SURVEY_BEFORE_CLOSURE | ANOMALY |

All six fixtures are labelled as anomalies.

The expected-detection descriptions provide the intended validation criteria for each scenario.

## 5. Evaluation Considerations

These fixtures can serve as a starting point for evaluating future data-quality and anomaly-detection logic.

A future evaluation process could:

1. Load each fixture independently.
2. Run the corresponding validation rule.
3. Record whether the issue was detected.
4. Compare the detection result with the ground-truth label.
5. Calculate detection metrics such as precision, recall and F1-score when both normal and anomalous evaluation records are available.

The current project defines the anomaly scenarios and ground-truth labels. It does not claim measured precision, recall or F1-score for an anomaly-detection model.

## 6. Design Rationale

The scenarios cover different operational risk areas:

- Referential integrity.
- Timestamp and lifecycle consistency.
- SLA accounting.
- Repeat-complaint tracking.
- Priority-based assignment.
- Customer satisfaction workflow.

Keeping these fixtures separate from the valid generated dataset allows the operational data to remain valid while still providing explicit examples of important failure conditions.

This approach supports future testing, validation-rule development and anomaly-detection evaluation without silently introducing corrupted records into the normal complaint workflow.
