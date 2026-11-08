# AI-Assisted Development Report and Prompt History

**Project:** YottaFlex Complaint Management System  
**Assessment:** Associate AI Forward Deployed Engineer  
**Primary AI Tool:** ChatGPT  
**Development Approach:** AI-assisted individual development  
**Project Stack:** Python, FastAPI, SQLAlchemy, SQLite, React, TypeScript and Vite

---

# 1. Overview of AI-Assisted Development

AI assistance was used as a development partner throughout the design, implementation, debugging, testing and documentation of the complaint management system.

The development approach focused on using AI to accelerate repetitive engineering tasks, explore architectural options, identify implementation issues and improve code quality.

The candidate remained responsible for integrating the generated suggestions, making implementation decisions, executing the application and verifying its behavior.

The AI-assisted workflow was divided into the following stages:

1. Requirements analysis and technical planning.
2. System architecture and database design.
3. Business rules and complaint classification.
4. Synthetic data generation.
5. Backend API development.
6. Workflow and SLA implementation.
7. Frontend development.
8. Analytics and operational monitoring.
9. Testing, validation and debugging.
10. Documentation and submission preparation.

# 2. AI Tools and Their Intended Roles

## Primary tool

### ChatGPT

**Role:** Technical planning, architecture discussions, implementation assistance, debugging, test design and documentation.

ChatGPT was used to break down the assessment into manageable engineering tasks, explain technical decisions, review implementation approaches and help resolve development issues.

## Other tools considered

| Tool | Potential engineering use |
|---|---|
| GitHub Copilot | IDE-based code completion and repetitive implementation |
| Claude | Alternative architecture review and code analysis |
| Gemini | Technical research and alternative implementation approaches |

These are possible complementary tools in an AI-assisted development workflow, not additional tools claimed as used for this project.

# 3. Prompt History

The following prompts are organized by development phase. They represent the engineering requests that form the basis of the project workflow. Wording has been consolidated for readability rather than presented as a verbatim transcript.

## Phase 1 — Requirements Analysis

### Prompt 01: Understand the assignment

I have received a technical assessment for an Associate AI Forward Deployed Engineer position. Analyze the complaint-management requirements and break them into functional requirements, non-functional requirements, data requirements, business rules and deliverables. Identify dependencies between tasks and recommend an implementation sequence suitable for a 72-hour challenge.

### Prompt 02: Identify system components

Based on the assessment, identify the major components required for an end-to-end complaint-management system. Consider customer management, orders, complaints, classification, prioritization, assignments, SLA tracking, communication, resolutions, surveys and analytics.

### Prompt 03: Identify edge cases

Identify important real-world complaint-management edge cases. Include repeat complaints, missing order information, product safety incidents, vulnerable customers, refund delays, reopened complaints and incorrect agent assignments. Explain how each should be handled.

### Prompt 04: Establish project scope

Recommend a realistic implementation scope that demonstrates medium-complexity engineering without introducing unnecessary infrastructure. Prioritize a working local application, deterministic business rules, relational persistence, synthetic data and meaningful validation.

## Phase 2 — Architecture and Database Design

### Prompt 05: Design the architecture

Design a modular architecture using FastAPI, SQLAlchemy, SQLite, React and TypeScript. Separate API routes, business services, data models, schemas, generators and frontend components. Explain the responsibilities and communication between layers.

### Prompt 06: Design the relational schema

Design a normalized relational database containing Customer, Product, Order, Complaint, ComplaintMessage, Category, PriorityRule, Assignment, SLAClock, Resolution and Survey.

Define primary keys, foreign keys, cardinalities, optional relationships and many-to-many bridge tables.

### Prompt 07: Review entity relationships

Evaluate whether the proposed schema correctly represents customer-to-order, customer-to-complaint, order-to-product, complaint-to-product, complaint-to-message, complaint-to-assignment and complaint-to-resolution relationships.

Identify where additional bridge or supporting entities are necessary.

### Prompt 08: Establish identifier conventions

Recommend immutable, zero-padded identifiers for customers, orders, complaints, messages, SLA clocks and resolutions. Ensure that identifiers remain consistent across parent and child records.

### Prompt 09: Review persistence decisions

Compare SQLite with heavier database infrastructure for this assessment. Consider local setup complexity, portability, data integrity, performance and reproducibility.

## Phase 3 — Business Rules and Decision Engine

### Prompt 10: Complaint classification

Implement a deterministic complaint classification engine using keyword-based rules. Support ten complaint categories, define matching precedence and provide a fallback category for unmatched descriptions.

### Prompt 11: Severity evaluation

Design a separate severity evaluation function that identifies low, medium, high and critical complaints. Product safety incidents, injuries, electric shocks, smoke and fire should receive special treatment.

### Prompt 12: Priority calculation

Design an explainable priority engine using customer sentiment, order value, recurrence and vulnerable-customer indicators.

Define configurable scoring weights and priority thresholds. Ensure product safety overrides ordinary scoring and always results in P1.

### Prompt 13: Decision traceability

Design a way to record priority decisions, calculated scores, applied rules, safety overrides and explanations. Ensure that an operations reviewer can understand why a complaint received a particular priority.

### Prompt 14: Team and agent assignment

Implement deterministic workload-aware assignment. Consider team eligibility, agent availability, active status, current workload and workload capacity. Route product safety complaints to Safety Response.

## Phase 4 — Synthetic Data Generation

### Prompt 15: Plan synthetic data generation

Design a reproducible synthetic data-generation pipeline for 5,000 customers, 500 products, 8,000 orders and 2,000 complaints.

Use a fixed seed and ensure that dependent records are generated only after their parent records exist.

### Prompt 16: Generate realistic relationships

Generate valid order items, complaint-product relationships, customer complaints and communication records. Ensure that monetary values and foreign-key relationships remain consistent.

### Prompt 17: Generate business scenarios

Introduce realistic synthetic scenarios such as repeated complaints, vulnerable-customer indicators, product safety incidents, missing orders, pending refunds and reopened cases.

Avoid assigning arbitrary ground-truth labels independently of the documented rules.

### Prompt 18: Create anomaly fixtures

Define six isolated anomaly fixtures covering missing customer references, impossible resolution chronology, incorrect SLA pause accounting, unlinked repeat issues, incorrect safety routing and surveys submitted before closure.

Maintain separate ground-truth labels.

### Prompt 19: Export generated records

Implement CSV, JSON and SQL export functionality. Include table names, record counts, generation seed, output location and a source manifest.

## Phase 5 — Backend and API Development

### Prompt 20: Implement the database layer

Create SQLAlchemy models for the entities and supporting tables. Configure relationships, foreign keys, nullable references, uniqueness constraints and SQLite foreign-key enforcement.

### Prompt 21: Implement API endpoints

Design REST endpoints for complaint creation, listing, filtering, detail retrieval, status updates, messaging, resolution, reopening and surveys.

Include request validation, appropriate HTTP status codes and error handling.

### Prompt 22: Implement complaint creation

Implement the complete complaint-creation flow. It should associate a customer and optional order, classify the complaint, determine severity and priority, select a team and agent, create an SLA clock and record initial communication and events.

### Prompt 23: Implement lifecycle validation

Implement allowed complaint status transitions. Prevent invalid state changes and record each transition with its previous state, new state, actor and timestamp.

### Prompt 24: Implement resolution and reopening

Implement resolution and closure operations. Support reopening a resolved complaint without deleting its previous resolution or event history. Create a new SLA cycle for reopened work.

### Prompt 25: Implement message handling

Support CUSTOMER, AGENT and SYSTEM messages. Validate message visibility and sender permissions. Use the first customer-visible agent response for response SLA tracking.

### Prompt 26: Implement post-resolution surveys

Allow survey submission only after complaint closure. Verify the associated final resolution, enforce rating limits and prevent duplicate submissions.

## Phase 6 — SLA Management

### Prompt 27: Calculate SLA targets

Implement priority-based response and resolution targets for P1, P2, P3 and P4 complaints. Keep target values configurable.

### Prompt 28: Implement pause and resume

When a complaint enters PENDING_CUSTOMER, pause the resolution clock. When work resumes, calculate the paused duration, update accumulated pause seconds and extend the resolution deadline.

The response clock must remain unaffected.

### Prompt 29: Evaluate SLA breaches

Calculate response and resolution breaches independently. Handle active, paused, resolved and reopened complaint cycles correctly.

### Prompt 30: Review SLA edge cases

Review timezone normalization, missing response timestamps, deadline comparisons, paused clocks and multiple SLA cycles. Identify possible inconsistencies between stored and dynamically calculated breach values.

## Phase 7 — Frontend Development

### Prompt 31: Design the dashboard

Create a React and TypeScript operational dashboard with complaint KPIs, open complaints, priority distribution, status information and navigation to the main application sections.

### Prompt 32: Build complaint management

Create a searchable and filterable complaint listing. Display customer information, complaint category, priority, status, assignment and SLA information.

### Prompt 33: Build complaint details

Design a detailed complaint view containing the description, customer and order context, classification, priority explanation, assignment history, messages, SLA clocks, resolutions and lifecycle events.

### Prompt 34: Build complaint creation

Implement a complaint submission form with customer selection, optional order association, channel, description and sentiment. Display the classification and assignment returned by the backend.

### Prompt 35: Build SLA monitoring

Create an SLA monitoring page that identifies active complaints, response deadlines, resolution deadlines, paused clocks and SLA breach indicators.

### Prompt 36: Build analytics

Create operational analytics for complaint volume, priority distribution, category distribution, lifecycle status, SLA performance and customer satisfaction.

### Prompt 37: Review frontend integration

Check API response structures against TypeScript interfaces. Identify missing fields, loading-state issues, error handling problems and inconsistent metric calculations.

## Phase 8 — Testing and Debugging

### Prompt 38: Business-rule testing

Create unit tests for classification, severity evaluation, priority thresholds, safety overrides and recurrence handling.

### Prompt 39: SLA testing

Test response and resolution deadlines, pause/resume calculations, paused duration accumulation, deadline extensions and reopened SLA cycles.

### Prompt 40: Lifecycle testing

Test valid and invalid status transitions, resolution, closure, reopening and event-history preservation.

### Prompt 41: API testing

Test complaint creation, filtering, detail retrieval, messaging, resolution, survey submission and invalid request handling.

### Prompt 42: Database integrity testing

Validate primary-key uniqueness, foreign-key references, enum values, timestamps, monetary calculations, lifecycle consistency and duplicate records.

### Prompt 43: Debugging assistance

Analyze the supplied Python, SQLAlchemy, FastAPI or TypeScript error. Identify its root cause, explain why it occurs and provide a complete correction compatible with the existing project structure.

### Prompt 44: Full project review

Review the implementation against the assessment requirements. Identify missing functionality, unsupported claims, inconsistent documentation and unverified assumptions.

## Phase 9 — Documentation and Submission

### Prompt 45: Write the README

Prepare a project README covering the problem statement, architecture, technologies, database entities, business rules, setup instructions, generator commands, API endpoints, validation results and limitations.

### Prompt 46: Prepare the data dictionary

Document all database tables, columns, data types, primary keys, foreign keys, nullability and entity relationships.

### Prompt 47: Document business rules

Explain classification precedence, severity evaluation, priority scoring, safety overrides, assignment decisions, SLA targets and complaint lifecycle transitions.

### Prompt 48: Document anomaly scenarios

Describe each anomaly fixture, affected entity, expected detection and ground-truth label. Clearly separate anomaly fixtures from valid operational records.

### Prompt 49: Prepare the technical walkthrough

Prepare explanations for architecture, database design, decision traceability, synthetic data generation, SLA behavior, validation strategy, trade-offs and known limitations.

---

# 4. AI Contribution and Candidate Ownership

## 4.1 Areas where AI accelerated development

AI assistance was particularly useful in:

- Breaking down a broad assessment into implementable modules.
- Exploring relational schema design and entity relationships.
- Drafting deterministic business-rule implementations.
- Structuring FastAPI routes and Pydantic schemas.
- Identifying edge cases in SLA and lifecycle logic.
- Creating test cases for business rules and workflow transitions.
- Resolving integration errors.
- Producing technical documentation.

## 4.2 Areas involving substantial AI assistance

The most AI-intensive areas were:

1. Initial architecture and database design.
2. Backend service and API implementation.
3. SLA and lifecycle edge-case analysis.
4. Synthetic data-generation logic.
5. Frontend component implementation.
6. Documentation and code-review support.

AI suggestions were treated as implementation assistance rather than automatically correct solutions.

## 4.3 Candidate review and validation responsibilities

The candidate's engineering responsibilities included:

- Selecting the technology stack.
- Maintaining the project structure.
- Integrating code into the actual repository.
- Configuring the local Python and Node environments.
- Executing database and generator commands.
- Running the API and frontend.
- Inspecting database records.
- Running automated tests.
- Testing application workflows.
- Reviewing validation output.
- Identifying and correcting integration issues.
- Reviewing documentation against implemented behavior.

The candidate remained responsible for understanding the implemented system and explaining its decisions.

# 5. Architecture and Design Decisions

| Decision | Rationale | Trade-off |
|---|---|---|
| FastAPI backend | Lightweight API development and request validation | Requires clear service-layer organization |
| SQLite | Simple, portable local persistence | Limited concurrent-write scalability |
| SQLAlchemy | Structured relational persistence and ORM relationships | Additional model and session management |
| React and TypeScript | Component-based interactive interface | Requires API/interface coordination |
| Deterministic classification | Explainable and reproducible decisions | Less flexible than trained language models |
| Weighted priority rules | Transparent business decisions | Weights require business calibration |
| Explicit event history | Preserves operational traceability | Additional storage and implementation complexity |
| Synthetic datasets | Safe, reproducible testing | Cannot represent every real customer behavior |
| Separate anomaly fixtures | Protects valid dataset integrity | Requires a separate evaluation process |

# 6. Business Assumptions

The following values are project assumptions rather than externally mandated standards.

## Priority scoring

- Strongly negative sentiment: +3.
- Negative sentiment: +2.
- Neutral sentiment: +1.
- High order value: up to +2.
- Recurrence: up to +3.
- Vulnerable-customer indicator: +1.
- Product safety: unconditional P1 override.

Priority thresholds:

| Score | Priority |
|---|---|
| 7+ | P1 |
| 5–6 | P2 |
| 3–4 | P3 |
| 0–2 | P4 |

## SLA targets

| Priority | Response | Resolution |
|---|---:|---:|
| P1 | 15 minutes | 4 hours |
| P2 | 1 hour | 12 hours |
| P3 | 4 hours | 48 hours |
| P4 | 8 hours | 72 hours |

Resolution SLA time pauses while awaiting customer information. Response SLA time does not pause.

## Classification

One primary category is assigned to each complaint. Multiple affected products are represented through a bridge relationship.

# 7. Testing and Verification Strategy

Testing was organized into several layers.

## Unit testing

Business-rule tests cover:

- Category classification.
- Severity determination.
- Priority calculation.
- Safety override.
- Priority threshold boundaries.

## Workflow testing

Workflow tests cover:

- Valid status transitions.
- Invalid transition rejection.
- SLA pause and resume.
- Resolution and closure.
- Reopening.
- Event-history preservation.

## Data validation

The data validator checks:

- Primary-key uniqueness.
- Foreign-key integrity.
- Valid categories and enumerated values.
- Chronological consistency.
- Monetary arithmetic.
- Complaint lifecycle rules.
- Priority decisions.
- Assignment consistency.
- Message and survey integrity.

## Integration and UI verification

The application was checked through:

- FastAPI endpoints.
- Swagger documentation.
- React frontend interaction.
- Complaint creation.
- Assignment display.
- SLA monitoring.
- Resolution and closure.
- Survey submission.
- Analytics consistency.

## Recorded verification results

| Verification | Result |
|---|---|
| Full dataset validation | 70,521 passed |
| Validation warnings | 0 |
| Validation failures | 0 |
| Backend automated tests | 35 passed |
| Frontend production build | Successful |
| Full synthetic dataset | 58,593 exported records |

These are the recorded project results, not claims of performance under production traffic.

# 8. Known Limitations

1. Classification uses deterministic keyword matching rather than a trained ML model.
2. Priority weights and SLA targets are illustrative assumptions.
3. SQLite is intended for local demonstration rather than high-concurrency production use.
4. Authentication and role-based access control are not implemented.
5. External email, SMS, payment and refund integrations are not implemented.
6. Assignment does not use live workforce availability.
7. Anomaly fixtures are defined separately; a complete automated anomaly-detection evaluation engine is not implemented.
8. The application has not been deployed to a production hosting environment.
9. Synthetic data cannot reproduce every real-world complaint distribution.

# 9. Future Improvements

Potential improvements include:

- ML-based complaint classification with human review.
- Sentiment analysis using a validated model.
- Configurable business rules through an administrative interface.
- Role-based access control.
- PostgreSQL deployment for concurrent operations.
- Real email and messaging integrations.
- Workforce-aware assignment using live availability.
- Automated anomaly detection and evaluation metrics.
- Production monitoring, logging and alerting.
- Load and performance testing.

# 10. Final Engineering Perspective

The purpose of AI assistance was to accelerate engineering work while retaining a clear understanding of the system's architecture, business logic and operational behavior.

The resulting application demonstrates a modular complaint-management workflow with relational persistence, deterministic decision-making, SLA enforcement, lifecycle traceability, synthetic data generation, operational analytics and validation.

The most important engineering consideration was not simply generating code, but ensuring that the components worked together, that important decisions could be explained and that the resulting behavior could be verified locally.
