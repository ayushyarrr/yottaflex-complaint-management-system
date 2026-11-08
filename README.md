# YottaFlex Complaint Management System

An end-to-end complaint management and workflow automation system developed as part of the **Associate AI Forward Deployed Engineer** technical assessment for YottaFlex AI Technologies.

The system manages customer complaints from submission through classification, prioritization, assignment, SLA monitoring, resolution, closure, and customer feedback.

## 1. Project Overview

Customer support operations often involve complaints arriving through multiple channels, inconsistent prioritization, delayed assignments, missed service-level agreements (SLAs), and limited visibility into resolution history.

This project provides a centralized workflow that:

- Classifies complaints using deterministic, rule-based text classification.
- Determines severity and priority using configurable business rules.
- Routes complaints to appropriate support teams and agents.
- Tracks response and resolution SLAs.
- Supports customer communication and internal messages.
- Maintains historical status transitions and assignment records.
- Records resolutions, complaint reopening, and customer surveys.
- Provides operational dashboards and analytics.
- Validates database integrity and identifies data-quality issues.

The application uses synthetic customer and transaction data. No real customer information is included.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data validation | Pydantic |
| Frontend | React, TypeScript |
| Frontend tooling | Vite |
| Testing | Pytest |
| Synthetic data | Faker, Python random |
| API documentation | FastAPI / Swagger UI |

The application runs locally and does not require a paid cloud service or external LLM API.

## 3. System Architecture

The application is organized into three main layers.

### Backend

The FastAPI backend handles:

- Complaint creation and retrieval.
- Classification and priority evaluation.
- Team and agent assignment.
- SLA calculations and monitoring.
- Status transitions and complaint lifecycle management.
- Resolution, reopening, messaging, and surveys.
- Operational analytics.

### Database

SQLite provides persistent storage for master data, transactional records, assignments, SLA clocks, resolutions, surveys, and historical events.

SQLAlchemy manages database models and relationships. Foreign-key enforcement is enabled for SQLite connections.

### Frontend

The React and TypeScript application provides:

- Operational dashboard.
- Complaint listing and filtering.
- Complaint details and workflow actions.
- SLA monitoring.
- Analytics and performance summaries.
- Complaint creation interface.

## 4. Database Design

The database includes 18 tables.

| Entity / Table | Purpose |
|---|---|
| Customer | Customer master records |
| Product | Product master records |
| Category | Complaint categories |
| Order | Customer orders |
| OrderItem | Products associated with orders |
| Complaint | Main complaint records |
| ComplaintProduct | Products associated with complaints |
| ComplaintMessage | Customer, agent, and system messages |
| Team | Support teams |
| Agent | Support agents |
| Assignment | Complaint assignment history |
| PriorityRule | Configured priority rules |
| PriorityDecision | Recorded priority evaluations |
| PriorityDecisionRule | Rules contributing to priority decisions |
| SLAClock | Response and resolution SLA tracking |
| Resolution | Complaint resolution records |
| Survey | Customer satisfaction feedback |
| ComplaintEvent | Historical workflow events |

Relationships include one-to-many and many-to-many associations. For example, customers can have multiple complaints, orders can contain multiple products through OrderItem, and complaints can reference multiple products through ComplaintProduct.

Order association is optional for complaints where an order cannot be identified or is not applicable.

## 5. Complaint Classification and Priority

### Classification

The classification engine uses keyword-based rules to identify complaint categories.

Supported categories:

1. Delivery
2. Refund
3. Payment
4. Damaged Product
5. Product Safety
6. Missing Item
7. Cancellation
8. Warranty
9. Account
10. Other

Severity is determined separately using description keywords and predefined severity conditions.

### Priority evaluation

Priority is calculated using:

- Customer sentiment.
- Order value.
- Complaint recurrence.
- Synthetic vulnerable-customer flag.
- Product safety risk.

The priority levels are:

| Priority | Meaning |
|---|---|
| P1 | Critical |
| P2 | High |
| P3 | Medium |
| P4 | Low |

**Safety override:** Product safety risks are automatically assigned P1 priority and routed to the Safety Response team.

The scoring weights and thresholds are documented business-rule assumptions for this assessment, rather than externally supplied industry standards.

## 6. Assignment and SLA Management

Complaints are routed to support teams based on their category.

The system includes five teams:

- Delivery Support
- Finance Support
- Product Support
- Safety Response
- General Support

Agent assignment considers team membership, agent activity, and workload.

### SLA targets

The following illustrative targets are configured:

| Priority | First response | Resolution |
|---|---:|---:|
| P1 | 15 minutes | 4 hours |
| P2 | 1 hour | 12 hours |
| P3 | 4 hours | 48 hours |
| P4 | 8 hours | 72 hours |

These targets are configurable project assumptions.

The resolution SLA clock can pause while awaiting customer information. The response SLA clock does not pause. Paused duration is tracked, and the resolution deadline is extended accordingly.

## 7. Complaint Lifecycle

The application supports these principal statuses:

`NEW → ASSIGNED → IN_PROGRESS → PENDING_CUSTOMER → RESOLVED → CLOSED`

The workflow also supports:

- Resuming work after a customer response.
- Resolving complaints.
- Closing resolved complaints.
- Reopening resolved complaints.
- Recording additional messages.
- Maintaining historical events across status changes.

Workflow history is stored as explicit events instead of relying solely on the complaint's current status.

A reopened complaint retains its earlier resolution and SLA history while creating a new resolution/SLA cycle as applicable.

## 8. Synthetic Dataset

The full dataset was generated using a fixed seed:

`20261022`

This makes the generated dataset reproducible using the same generator configuration.

### Generated master and transactional data

| Record type | Count |
|---|---:|
| Customers | 5,000 |
| Products | 500 |
| Orders | 8,000 |
| Order items | 15,850 |
| Complaints | 2,000 |
| Complaint messages | 6,000 |
| Complaint-product links | 2,901 |
| Priority decisions | 2,000 |
| Priority decision-rule links | 3,204 |
| Categories | 10 |
| Priority rules | 9 |
| Teams | 5 |
| Agents | 14 |

### Workflow records

| Record type | Count |
|---|---:|
| Assignments | 1,900 |
| SLA clocks | 2,000 |
| Lifecycle events | 8,350 |
| Resolutions | 700 |
| Surveys | 150 |

The final complaint status distribution is:

| Status | Count |
|---|---:|
| NEW | 100 |
| ASSIGNED | 400 |
| IN_PROGRESS | 500 |
| PENDING_CUSTOMER | 300 |
| RESOLVED | 400 |
| CLOSED | 300 |
| **Total** | **2,000** |

The 100 NEW complaints have no assignment yet. The remaining 1,900 complaints have assignments.

### Dataset exports

The full database was exported into CSV and JSON files for each of its 18 tables, alongside a complete SQLite SQL dump and an export manifest.

Location:

`data/generated/full/`

## 9. Data Quality and Validation

The project includes a database validation utility that checks:

- Primary-key and foreign-key integrity.
- Required relationships.
- Valid enum values.
- Complaint classification consistency.
- Priority and safety override rules.
- Timestamp chronology.
- Resolution and survey lifecycle consistency.
- SLA clock consistency.
- Assignment and workflow records.
- Expected generated record counts.

The full dataset passed validation with:

| Result | Count |
|---|---:|
| Passed checks | 70,521 |
| Warnings | 0 |
| Failed checks | 0 |

**Final validation result: PASSED**

### Anomaly scenarios

Six separate anomaly fixtures are maintained under:

- `data/anomalies/`
- `data/ground_truth/`

They cover:

1. Complaint without a customer.
2. Resolution timestamp preceding complaint creation.
3. Incorrect SLA pause duration.
4. Repeat complaint not linked correctly.
5. Critical safety complaint assigned to the wrong team.
6. Survey submitted before complaint closure.

These are deliberately defined test fixtures with corresponding ground-truth labels. They are kept separate from the valid generated database.

## 10. Running the Project Locally

### Prerequisites

- Python 3.11 or later.
- Node.js and npm.
- Git.

### Backend setup

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the backend:

```powershell
uvicorn backend.app.main:app --reload
```

Backend API:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

### Frontend setup

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local frontend URL displayed by Vite, normally:

`http://localhost:5173`

### Running automated tests

From the project root with the virtual environment activated:

```powershell
python -m pytest backend/tests -v
```

## 11. Generating the Full Dataset

The following commands generate the full dataset in a separate SQLite database.

Set the database environment variable first:

```powershell
$env:YOTTAFLEX_DATABASE_URL="sqlite:///./complaints_full.db"
```

Generate master data:

```powershell
python -m backend.generator.generate --mode full
```

Generate teams and agents:

```powershell
python -m backend.generator.generate_teams
```

Generate complaints and messages:

```powershell
python -m backend.generator.generate_complaints --mode full
```

Generate assignments and SLA clocks:

```powershell
python -m backend.generator.generate_workflow
```

Generate lifecycle histories:

```powershell
python -m backend.generator.generate_lifecycle
```

Validate the generated database:

```powershell
python -m backend.generator.validate --mode full
```

Export the database:

```powershell
python -m backend.generator.export_data
```

The full database is stored as `complaints_full.db`. The default application database remains separate.

## 12. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/complaints` | List complaints |
| POST | `/api/complaints` | Create complaint |
| GET | `/api/complaints/{id}` | Retrieve complaint details |
| PATCH | `/api/complaints/{id}/status` | Change complaint status |
| POST | `/api/complaints/{id}/resolve` | Resolve complaint |
| POST | `/api/complaints/{id}/reopen` | Reopen complaint |
| POST | `/api/complaints/{id}/messages` | Add complaint message |
| POST | `/api/complaints/{id}/survey` | Submit customer survey |
| GET | `/api/analytics` | Retrieve operational analytics |

## 13. Project Structure

```text
yottaflex-complaint-system/
│
├── backend/
│   ├── app/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── database.py
│   │   └── main.py
│   │
│   ├── generator/
│   │   ├── generate.py
│   │   ├── generate_complaints.py
│   │   ├── generate_teams.py
│   │   ├── generate_workflow.py
│   │   ├── generate_lifecycle.py
│   │   ├── lifecycle_config.py
│   │   ├── rules.py
│   │   ├── validate.py
│   │   └── export_data.py
│   │
│   └── tests/
│
├── frontend/
│
├── data/
│   ├── generated/
│   ├── anomalies/
│   └── ground_truth/
│
├── docs/
│
├── prompts/
│
├── requirements.txt
├── README.md
└── .gitignore
```

## 14. Assumptions and Limitations

- Complaint classification is deterministic and keyword-based; it is not a trained machine-learning classifier.
- Priority scores, scoring weights, and SLA targets are illustrative business assumptions.
- The dataset is synthetic and is not representative of actual YottaFlex customer operations.
- The system uses SQLite for local execution rather than a production database server.
- Agent assignment uses deterministic workload-aware logic rather than a live workforce scheduling integration.
- No external customer communication provider or payment/refund provider is integrated.
- Anomaly fixtures are maintained separately from the valid production-style dataset.
- The application is intended as an assessment prototype and requires additional security, scalability, authentication, and deployment work before production use.

## 15. Reproducibility and AI Assistance

The synthetic data generator uses a fixed seed of `20261022`.

The project includes generated data, validation utilities, and automated tests to support repeatable verification.

AI assistance was used during development. Relevant prompts and assistance records are maintained in the project for assessment transparency.
