# Database Data Dictionary

## 1. Overview

The YottaFlex Complaint Management System uses an SQLite relational database managed through SQLAlchemy.

The full generated database contains 18 tables covering customer master data, products, orders, complaints, prioritization, assignments, SLA tracking, resolutions, surveys and workflow events.

**Database:** `complaints_full.db`

**Total tables:** 18

**Generated dataset seed:** `20261022`

## 2. Entity Definitions

### 2.1 Customers

**Table:** `customers`

Stores customer master information.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| customer_id | VARCHAR(20) | PK | No | Unique customer identifier |
| full_name | VARCHAR(100) | | No | Customer name |
| email | VARCHAR(150) | | No | Customer email |
| phone | VARCHAR(20) | | No | Customer phone number |
| region | VARCHAR(100) | | No | Customer region |
| is_vulnerable | BOOLEAN | | No | Synthetic vulnerable-customer indicator |
| status | VARCHAR(20) | | No | Customer record status |
| created_at | DATETIME | | No | Record creation timestamp |

### 2.2 Products

**Table:** `products`

Stores product master information.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| product_id | VARCHAR(30) | PK | No | Unique product identifier |
| product_name | VARCHAR(150) | | No | Product name |
| category_name | VARCHAR(100) | | No | Product category |
| unit_price | NUMERIC(12,2) | | No | Product unit price |
| is_safety_sensitive | BOOLEAN | | No | Indicates safety-sensitive product |
| status | VARCHAR(30) | | No | Product status |
| created_at | DATETIME | | No | Record creation timestamp |

### 2.3 Categories

**Table:** `categories`

Stores complaint classification categories.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| category_id | INTEGER | PK | No | Category identifier |
| category_name | VARCHAR(100) | | No | Category name |
| description | TEXT | | Yes | Category description |
| is_active | BOOLEAN | | No | Category availability |

### 2.4 Orders

**Table:** `orders`

Stores customer order information.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| order_id | VARCHAR(30) | PK | No | Unique order identifier |
| customer_id | VARCHAR(20) | FK | No | References customers.customer_id |
| order_date | DATETIME | | No | Order date |
| total_amount | NUMERIC(12,2) | | No | Total order value |
| payment_status | VARCHAR(30) | | No | Payment status |
| order_status | VARCHAR(30) | | No | Order status |
| shipping_region | VARCHAR(100) | | No | Shipping region |
| created_at | DATETIME | | No | Record creation timestamp |

### 2.5 Order Items

**Table:** `order_items`

Connects orders with products and records quantities and prices.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| order_item_id | INTEGER | PK | No | Order item identifier |
| order_id | VARCHAR(30) | FK | No | References orders.order_id |
| product_id | VARCHAR(30) | FK | No | References products.product_id |
| quantity | INTEGER | | No | Ordered quantity |
| unit_price | NUMERIC(12,2) | | No | Unit price at order time |
| line_total | NUMERIC(12,2) | | No | Quantity multiplied by unit price |

### 2.6 Complaints

**Table:** `complaints`

The primary transactional entity representing customer complaints.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| complaint_id | VARCHAR(30) | PK | No | Unique complaint identifier |
| customer_id | VARCHAR(20) | FK | No | References customers.customer_id |
| order_id | VARCHAR(30) | FK | Yes | References orders.order_id |
| category_id | INTEGER | FK | No | References categories.category_id |
| description | TEXT | | No | Customer complaint description |
| channel | VARCHAR(30) | | No | Complaint submission channel |
| sentiment | VARCHAR(30) | | No | Detected sentiment |
| severity | VARCHAR(30) | | No | Complaint severity |
| priority | VARCHAR(10) | | No | Assigned priority level |
| status | VARCHAR(30) | | No | Current complaint status |
| recurrence_count | INTEGER | | No | Number of related occurrences |
| created_at | DATETIME | | No | Complaint creation timestamp |
| updated_at | DATETIME | | No | Last update timestamp |

The order relationship is optional.

### 2.7 Complaint Products

**Table:** `complaint_products`

Bridge table connecting complaints and affected products.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| complaint_product_id | INTEGER | PK | No | Link identifier |
| complaint_id | VARCHAR(30) | FK | No | References complaints.complaint_id |
| product_id | VARCHAR(30) | FK | No | References products.product_id |
| issue_description | TEXT | | Yes | Product-specific issue description |

### 2.8 Complaint Messages

**Table:** `complaint_messages`

Stores customer, agent and system communication.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| message_id | VARCHAR(60) | PK | No | Unique message identifier |
| complaint_id | VARCHAR(30) | FK | No | References complaints.complaint_id |
| sender_type | VARCHAR(30) | | No | Message sender type |
| message_text | TEXT | | No | Message contents |
| channel | VARCHAR(30) | | No | Communication channel |
| is_internal | BOOLEAN | | No | Indicates internal-only message |
| created_at | DATETIME | | No | Message timestamp |

### 2.9 Teams

**Table:** `teams`

Stores operational support teams.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| team_id | INTEGER | PK | No | Team identifier |
| team_name | VARCHAR(100) | | No | Team name |
| description | TEXT | | Yes | Team description |
| is_active | BOOLEAN | | No | Team availability |

### 2.10 Agents

**Table:** `agents`

Stores support agent information.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| agent_id | INTEGER | PK | No | Agent identifier |
| agent_name | VARCHAR(100) | | No | Agent name |
| team_id | INTEGER | FK | No | References teams.team_id |
| workload_capacity | INTEGER | | No | Configured workload capacity |
| is_active | BOOLEAN | | No | Agent availability |

### 2.11 Assignments

**Table:** `assignments`

Stores complaint assignment records and reassignment history.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| assignment_id | INTEGER | PK | No | Assignment identifier |
| complaint_id | VARCHAR(30) | FK | No | References complaints.complaint_id |
| team_id | INTEGER | FK | No | References teams.team_id |
| agent_id | INTEGER | FK | No | References agents.agent_id |
| assigned_at | DATETIME | | No | Assignment timestamp |
| assigned_by | VARCHAR(100) | | No | Assignment actor |
| reason | TEXT | | Yes | Assignment reason |
| is_current | BOOLEAN | | No | Indicates current assignment |

### 2.12 Priority Rules

**Table:** `priority_rules`

Stores configurable priority evaluation rules.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| rule_id | INTEGER | PK | No | Rule identifier |
| rule_name | VARCHAR(100) | | No | Rule name |
| condition_type | VARCHAR(50) | | No | Condition type |
| condition_value | VARCHAR(100) | | No | Condition value |
| score | INTEGER | | No | Score contribution |
| priority_override | VARCHAR(10) | | Yes | Optional priority override |
| is_active | BOOLEAN | | No | Rule availability |
| effective_from | DATETIME | | No | Effective start date |
| effective_to | DATETIME | | Yes | Optional effective end date |

### 2.13 Priority Decisions

**Table:** `priority_decisions`

Stores recorded priority evaluation results.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| decision_id | INTEGER | PK | No | Decision identifier |
| complaint_id | VARCHAR(30) | FK | No | References complaints.complaint_id |
| calculated_score | INTEGER | | No | Calculated priority score |
| assigned_priority | VARCHAR(10) | | No | Resulting priority |
| safety_override_applied | VARCHAR(10) | | Yes | Safety override indicator |
| explanation | VARCHAR(500) | | No | Decision explanation |
| decided_at | DATETIME | | No | Decision timestamp |

### 2.14 Priority Decision Rules

**Table:** `priority_decision_rules`

Bridge table connecting priority decisions and the rules that influenced them.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| id | INTEGER | PK | No | Link identifier |
| decision_id | INTEGER | FK | No | References priority_decisions.decision_id |
| rule_id | INTEGER | FK | No | References priority_rules.rule_id |

### 2.15 SLA Clocks

**Table:** `sla_clocks`

Tracks response and resolution deadlines, pauses and breaches.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| sla_id | VARCHAR(60) | PK | No | SLA clock identifier |
| complaint_id | VARCHAR(30) | FK | No | References complaints.complaint_id |
| priority | VARCHAR(10) | | No | Priority used for SLA targets |
| response_deadline | DATETIME | | No | First response deadline |
| resolution_deadline | DATETIME | | No | Resolution deadline |
| first_response_at | DATETIME | | Yes | First public agent response |
| resolved_at | DATETIME | | Yes | Resolution timestamp |
| paused_at | DATETIME | | Yes | Current pause start |
| total_paused_seconds | INTEGER | | No | Accumulated paused duration |
| response_breached | BOOLEAN | | No | Response breach indicator |
| resolution_breached | BOOLEAN | | No | Resolution breach indicator |
| created_at | DATETIME | | No | SLA clock creation timestamp |

### 2.16 Resolutions

**Table:** `resolutions`

Stores complaint resolution attempts and final resolutions.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| resolution_id | VARCHAR(60) | PK | No | Resolution identifier |
| complaint_id | VARCHAR(30) | FK | No | References complaints.complaint_id |
| resolution_type | VARCHAR(50) | | No | Resolution type |
| resolution_description | TEXT | | No | Resolution details |
| resolved_by | INTEGER | FK | No | References agents.agent_id |
| resolved_at | DATETIME | | No | Resolution timestamp |
| is_final | BOOLEAN | | No | Indicates final resolution |

### 2.17 Surveys

**Table:** `surveys`

Stores customer feedback after complaint closure.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| survey_id | INTEGER | PK | No | Survey identifier |
| resolution_id | VARCHAR(60) | FK | No | References resolutions.resolution_id |
| complaint_id | VARCHAR(30) | FK | No | References complaints.complaint_id |
| rating | INTEGER | | No | Customer rating from 1 to 5 |
| feedback | TEXT | | Yes | Optional feedback |
| submitted_at | DATETIME | | No | Submission timestamp |

The resolution_id relationship is unique in the database, allowing at most one survey per resolution.

### 2.18 Complaint Events

**Table:** `complaint_events`

Stores historical workflow and status changes.

| Column | Type | Key | Nullable | Description |
|---|---|---|---|---|
| event_id | INTEGER | PK | No | Event identifier |
| complaint_id | VARCHAR(30) | FK | No | References complaints.complaint_id |
| event_type | VARCHAR(50) | | No | Event type |
| old_value | VARCHAR(100) | | Yes | Previous value |
| new_value | VARCHAR(100) | | Yes | New value |
| description | TEXT | | Yes | Event description |
| performed_by | VARCHAR(100) | | No | Actor responsible |
| created_at | DATETIME | | No | Event timestamp |

## 3. Relationship Summary

| Parent | Child / Bridge | Relationship |
|---|---|---|
| Customer | Order | One-to-many |
| Customer | Complaint | One-to-many |
| Order | OrderItem | One-to-many |
| Product | OrderItem | One-to-many |
| Complaint | ComplaintProduct | One-to-many |
| Product | ComplaintProduct | One-to-many |
| Category | Complaint | One-to-many |
| Complaint | ComplaintMessage | One-to-many |
| Complaint | Assignment | One-to-many |
| Team | Agent | One-to-many |
| Team | Assignment | One-to-many |
| Agent | Assignment | One-to-many |
| Complaint | SLAClock | One-to-many |
| Complaint | Resolution | One-to-many |
| Agent | Resolution | One-to-many |
| Resolution | Survey | One-to-zero-or-one |
| Complaint | Survey | One-to-many |
| Complaint | ComplaintEvent | One-to-many |
| Complaint | PriorityDecision | One-to-many |
| PriorityDecision | PriorityDecisionRule | One-to-many |
| PriorityRule | PriorityDecisionRule | One-to-many |

The OrderItem bridge supports a many-to-many relationship between orders and products. ComplaintProduct supports a many-to-many relationship between complaints and products. PriorityDecisionRule connects priority decisions with the rules contributing to each decision.

## 4. Data Integrity Notes

- Every table has a primary key.
- Foreign keys enforce the documented relationships.
- Complaint order association is optional.
- Assignment records preserve historical assignments through `is_current`.
- Multiple SLA clocks and resolution records can exist for a complaint.
- Survey resolution references are unique.
- Complaint events preserve workflow history.
- SQLite foreign-key enforcement is enabled by the application database configuration.

## 5. Generated Full Dataset Counts

| Table | Records |
|---|---:|
| agents | 14 |
| assignments | 1,900 |
| categories | 10 |
| complaint_events | 8,350 |
| complaint_messages | 6,000 |
| complaint_products | 2,901 |
| complaints | 2,000 |
| customers | 5,000 |
| order_items | 15,850 |
| orders | 8,000 |
| priority_decision_rules | 3,204 |
| priority_decisions | 2,000 |
| priority_rules | 9 |
| products | 500 |
| resolutions | 700 |
| sla_clocks | 2,000 |
| surveys | 150 |
| teams | 5 |
| **Total** | **58,593** |

## 6. Schema Source

This dictionary was prepared from the actual SQLAlchemy-inspected schema of `complaints_full.db`, including column types, nullability, primary keys and foreign-key definitions.

It describes the generated database schema, not an independently proposed schema.
