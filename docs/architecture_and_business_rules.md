# System Architecture and Business Rules

## 1. Purpose

The YottaFlex Complaint Management System is designed to manage customer complaints through a structured operational workflow.

The system combines deterministic classification, priority evaluation, workload-aware assignment, SLA monitoring, lifecycle management, customer communication and operational analytics.

The architecture separates the frontend, API layer, business logic, database and synthetic data-generation utilities.

## 2. High-Level Architecture

```text
                    CUSTOMER / OPERATIONS USER
                              |
                              v
                    REACT + TYPESCRIPT UI
                              |
                              v
                       FASTAPI BACKEND
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
   COMPLAINT SERVICE    PRIORITY ENGINE      SLA SERVICE
          |                   |                   |
          v                   v                   v
   CLASSIFICATION       RULE EVALUATION     CLOCK MANAGEMENT
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                      SQLALCHEMY ORM
                              |
                              v
                         SQLITE DB
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
     ASSIGNMENTS          WORKFLOW EVENTS       ANALYTICS
          |
          v
     SUPPORT TEAMS / AGENTS
```

The data-generation and validation utilities operate separately from the application runtime.

## 3. Technology and Component Responsibilities

### Frontend

React and TypeScript provide the user interface for:

- Operational dashboard.
- Complaint listing and filtering.
- Complaint details.
- Complaint creation.
- Status and resolution actions.
- SLA monitoring.
- Operational analytics.

The frontend communicates with the backend through HTTP API requests.

### API Layer

FastAPI exposes REST endpoints for complaint management, workflow actions and analytics.

Pydantic schemas validate incoming request data and structure API responses.

### Business Logic

The backend services are responsible for:

- Complaint classification.
- Severity evaluation.
- Priority calculation.
- Team and agent assignment.
- SLA deadline calculations.
- Status transition validation.
- Resolution and reopening.
- Message and survey validation.

### Persistence

SQLAlchemy manages database access and entity relationships.

SQLite provides local persistent storage. Foreign-key enforcement is enabled for SQLite connections.

## 4. Complaint Processing Pipeline

A complaint follows these main processing stages:

1. Complaint submission.
2. Customer and optional order association.
3. Category classification.
4. Severity determination.
5. Sentiment and priority evaluation.
6. Team and agent assignment.
7. SLA clock creation.
8. Customer and agent communication.
9. Work progression and status changes.
10. Resolution and closure.
11. Customer satisfaction survey.

The system records important decisions and workflow transitions so that operational actions can be traced.

## 5. Classification Engine

### Approach

The classification engine uses deterministic keyword matching.

The complaint description is converted to lowercase and checked against category-specific keyword lists.

Supported categories:

| Category | Example matching terms |
|---|---|
| Product Safety | unsafe, injury, overheating, smoke, fire |
| Damaged Product | broken, damaged, defective, cracked |
| Delivery | shipment, courier, delayed, tracking |
| Refund | refund, money back, reimbursement |
| Payment | payment, charged, transaction |
| Missing Item | missing, not received, item absent |
| Cancellation | cancel, cancellation |
| Warranty | warranty, repair, replacement |
| Account | login, password, sign in |
| Other | No matching category |

The category order is deterministic. When no configured category matches, the complaint is classified as OTHER.

### Severity determination

Severity is evaluated separately from category.

The current rules prioritize safety-related terms:

- CRITICAL: injury, electric shock, fire, smoke, explosion.
- HIGH: unsafe, dangerous, overheating, completely broken, serious.
- MEDIUM: damaged, defective, broken.
- LOW: No matching higher-severity condition.

The implementation uses keyword rules rather than a trained machine-learning model.

## 6. Priority Evaluation Engine

### Inputs

The priority engine evaluates:

- Customer sentiment.
- Associated order value.
- Complaint recurrence count.
- Vulnerable-customer indicator.
- Product safety risk.

### Scoring assumptions

The following weights are project-defined business assumptions.

| Condition | Score |
|---|---:|
| Strongly negative sentiment | +3 |
| Negative sentiment | +2 |
| Neutral sentiment | +1 |
| Positive sentiment | +0 |
| Order value above ₹10,000 | +2 |
| Order value ₹5,001–₹10,000 | +1 |
| Third or later complaint | +3 |
| Second complaint | +2 |
| Vulnerable-customer indicator | +1 |

### Priority thresholds

| Score | Priority |
|---|---|
| 7 or above | P1 |
| 5–6 | P2 |
| 3–4 | P3 |
| 0–2 | P4 |

### Safety override

Product safety takes precedence over the ordinary score-based priority calculation.

A safety-risk complaint is automatically assigned P1, regardless of its calculated score.

The system records the calculated score, resulting priority, explanation and applicable priority rules in the priority decision records.

This makes the decision traceable.

## 7. Team and Agent Assignment

The system routes complaints to teams based on category.

| Complaint category | Assigned team |
|---|---|
| Delivery | Delivery Support |
| Refund | Finance Support |
| Payment | Finance Support |
| Product Safety | Safety Response |
| Damaged Product | Product Support |
| Warranty | Product Support |
| Other categories | General Support |

The assignment engine considers:

- Team eligibility.
- Agent team membership.
- Agent active status.
- Current workload.
- Configured workload capacity.

A deterministic workload-aware selection process distributes assignments among eligible agents.

A complaint can retain historical assignment records while identifying the current assignment through the `is_current` field.

NEW complaints remain unassigned until they enter the assignment stage.

## 8. SLA Management

### SLA targets

The application uses the following illustrative targets:

| Priority | Response target | Resolution target |
|---|---:|---:|
| P1 | 15 minutes | 4 hours |
| P2 | 1 hour | 12 hours |
| P3 | 4 hours | 48 hours |
| P4 | 8 hours | 72 hours |

These targets are configuration assumptions for the assessment.

### Response clock

The response clock measures the time between complaint creation and the first customer-visible agent response.

Internal system messages do not count as a customer response.

### Resolution clock

The resolution clock measures the time until complaint resolution.

It supports pause and resume operations.

### Pause and resume behavior

When a complaint enters PENDING_CUSTOMER:

1. The current pause timestamp is recorded.
2. Resolution SLA time stops accumulating.
3. The response SLA remains unaffected.

When the complaint returns to IN_PROGRESS:

1. The pause duration is calculated.
2. Accumulated paused seconds are updated.
3. The resolution deadline is extended by the paused duration.
4. The pause timestamp is cleared.

SLA clock cycles are retained separately when a complaint is reopened.

### Breach evaluation

Response and resolution breaches are evaluated separately.

The application can report:

- Response breach count.
- Resolution breach count.
- Breach rates.
- Paused SLA clocks.
- Current SLA status.

## 9. Complaint Lifecycle and State Transitions

The principal lifecycle is:

```text
NEW
 |
 v
ASSIGNED
 |
 v
IN_PROGRESS
 |
 v
PENDING_CUSTOMER
 |
 v
IN_PROGRESS
 |
 v
RESOLVED
 |
 v
CLOSED
```

The system validates allowed status transitions rather than accepting arbitrary status changes.

### Supported operations

| Current status | Action | Result |
|---|---|---|
| ASSIGNED | Start work | IN_PROGRESS |
| IN_PROGRESS | Await customer | PENDING_CUSTOMER |
| PENDING_CUSTOMER | Resume work | IN_PROGRESS |
| IN_PROGRESS | Resolve | RESOLVED |
| RESOLVED | Close | CLOSED |
| RESOLVED | Reopen | New active work cycle |

CLOSED complaints are terminal in the current implementation.

### Historical traceability

Every important workflow transition creates a ComplaintEvent record.

The event history preserves:

- Event type.
- Previous value.
- New value.
- Description.
- Actor.
- Timestamp.

The current complaint status is stored separately from its historical events.

## 10. Resolution and Reopening

Resolution is permitted when a complaint is IN_PROGRESS.

The resolution operation records:

- Resolution type.
- Resolution description.
- Resolving agent.
- Resolution timestamp.
- Whether the resolution is final.

A complaint can be reopened from RESOLVED.

Reopening:

- Retains previous resolution records.
- Marks the earlier resolution as non-final.
- Creates a new SLA cycle.
- Records a reopening event.
- Returns the complaint to active work.

This preserves the earlier history rather than overwriting it.

## 11. Customer Communication

Complaint messages support three sender types:

- CUSTOMER
- AGENT
- SYSTEM

Messages include:

- Complaint reference.
- Sender type.
- Message text.
- Communication channel.
- Internal/public visibility.
- Creation timestamp.

Validation rules prevent customers from creating internal messages and prevent system-generated messages from being submitted through the ordinary user-message endpoint.

Customer-visible agent messages are used to identify first responses for SLA purposes.

## 12. Customer Satisfaction

Surveys are accepted only after complaint closure.

The application verifies:

- The complaint is CLOSED.
- The selected resolution belongs to the complaint.
- The resolution is final.
- No survey already exists for that resolution.
- The rating is between 1 and 5.

Survey records include rating, optional feedback and submission timestamp.

The analytics service uses survey records to calculate customer satisfaction metrics.

## 13. Analytics and Operational Metrics

The analytics layer provides visibility into complaint operations.

Metrics include:

- Total complaints.
- Complaint status distribution.
- Priority distribution.
- Category distribution.
- Response SLA performance.
- Resolution SLA performance.
- Average resolution performance.
- Customer satisfaction.
- Survey participation.

The SLA calculations are based on the SLA clock records and the application's breach-evaluation logic.

## 14. Data Generation and Reproducibility

Synthetic data is generated using a fixed seed:

`20261022`

The generation process creates master data before dependent transactional records.

The full dataset contains:

- 5,000 customers.
- 500 products.
- 8,000 orders.
- 2,000 complaints.
- 6,000 complaint messages.
- 1,900 assignments.
- 2,000 SLA clocks.
- 700 resolutions.
- 150 surveys.
- 8,350 lifecycle events.

The same generator architecture supports starter and full dataset modes.

The full database is exported into CSV, JSON and SQL formats.

## 15. Data Quality and Exception Scenarios

Six isolated anomaly fixtures are defined separately from the valid generated dataset.

| ID | Scenario | Expected detection |
|---|---|---|
| ANOM-001 | Complaint without customer | Missing customer relationship |
| ANOM-002 | Resolution before complaint | Invalid timestamp chronology |
| ANOM-003 | Incorrect SLA pause | Inconsistent pause duration and deadline |
| ANOM-004 | Repeat complaint not linked | Incorrect recurrence relationship |
| ANOM-005 | Critical safety complaint routed incorrectly | Safety routing violation |
| ANOM-006 | Survey before closure | Invalid lifecycle chronology |

Each fixture includes a ground-truth anomaly label and expected detection description.

These fixtures are test scenarios, not records inserted into the valid full database.

## 16. Validation Results

The full generated database was validated using:

```powershell
python -m backend.generator.validate --mode full
```

Recorded validation result:

| Metric | Result |
|---|---:|
| Passed checks | 70,521 |
| Warnings | 0 |
| Failed checks | 0 |

**Final result: PASSED**

Automated backend tests:

```powershell
python -m pytest backend/tests -v
```

Previously verified result: 35 tests passed.

Frontend production build:

```powershell
cd frontend
npm run build
```

Previously verified result: successful production build.

## 17. Design Assumptions and Limitations

1. Classification is deterministic keyword matching, not a trained ML classifier.
2. Priority weights and thresholds are illustrative business rules.
3. SLA targets are configurable assumptions, not externally mandated service standards.
4. Synthetic data is used instead of real customer records.
5. The local implementation uses SQLite.
6. Assignment is based on configured teams and workload, not live workforce availability.
7. No external email, SMS, payment or refund provider is integrated.
8. Authentication, authorization, production monitoring and deployment hardening are outside the current prototype scope.
9. The anomaly fixtures are maintained separately and are not evidence of a production anomaly-detection engine.

## 18. Architecture Rationale

The system uses a modular design so that classification, priority evaluation, assignment, SLA management, lifecycle operations and analytics can be changed independently.

Deterministic rules make decisions reproducible and explainable.

Explicit event history supports auditability.

Relational database constraints preserve entity relationships.

Separating synthetic data generation from application runtime allows the same application to operate with either a starter dataset or the full generated dataset.

The architecture is intended to demonstrate an explainable, traceable and testable complaint-management workflow that can be extended toward production requirements.
