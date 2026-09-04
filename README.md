# 📦 Inventory Management System

> **A production-oriented full-stack inventory operations platform built with FastAPI, SQLAlchemy 2.0, SQLite, and Streamlit.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python\&logoColor=white)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi\&logoColor=white)](#)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy\&logoColor=white)](#)
[![Streamlit](https://img.shields.io/badge/Streamlit-Operations%20Console-FF4B4B?logo=streamlit\&logoColor=white)](#)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite\&logoColor=white)](#)
[![Pytest](https://img.shields.io/badge/Tests-43%20Passing-22C55E?logo=pytest\&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)

---

## 🚀 Overview

The **Inventory Management System** is a full-stack business application designed to manage products, stock levels, suppliers, categories, purchase orders, and inventory health from a centralized operations console.

Unlike a simple CRUD application, this project implements a genuine **client-server architecture**:

```text
Streamlit Operations Console
          │
          │ HTTP / REST
          ▼
     FastAPI Backend
          │
          ▼
   Service Layer
          │
          ▼
 SQLAlchemy 2.0 ORM
          │
          ▼
       SQLite
```

The system focuses on the complete inventory operations lifecycle:

**Product → Stock → Low-Stock Detection → Reorder Suggestion → Purchase Order → Receiving → Inventory Update → Health Reporting**

The frontend communicates with the backend through real HTTP requests rather than directly importing business logic, creating a clean architectural boundary between presentation, API, and domain logic.

---

## 🎯 Problem Statement

Inventory-heavy businesses need more than a spreadsheet containing product quantities.

Operational teams need to answer questions such as:

* What products are currently in stock?
* Which products are approaching a stockout?
* Which products require immediate reordering?
* Which supplier should receive a purchase order?
* What happens when an order is received?
* How much inventory value is currently held?
* Is inventory health improving or deteriorating?

Poor inventory visibility can lead to:

* Stockouts
* Lost sales
* Overstocking
* Manual reorder calculations
* Data inconsistencies
* Incorrect purchase quantities
* Difficult operational reporting

This system addresses these problems through a centralized inventory management workflow with automated low-stock detection and purchase-order operations.

---

# ✨ Core Features

## 📦 Product Management

Manage a structured product catalog containing:

* Product names
* SKUs
* Categories
* Suppliers
* Unit prices
* Current stock quantities
* Low-stock thresholds

### Financial Data Integrity

Product prices are stored as **integer cents** rather than floating-point currency values.

```text
unit_price_cents = 1299
```

represents:

```text
$12.99
```

This avoids floating-point rounding problems during financial calculations.

The application exposes a display-oriented dollar representation while keeping the canonical stored value as an integer.

---

## 🚨 Intelligent Low-Stock Detection

The system automatically identifies products whose inventory has reached or fallen below their configured threshold.

Low-stock products are:

* detected through dedicated backend logic
* exposed through a dedicated API endpoint
* displayed prominently in the Operations Console
* sorted by severity / stock shortfall

Example:

```text
Current Stock:   4
Threshold:      10
Shortfall:       6
```

This allows operators to prioritize the most urgent inventory problems first.

---

## 🛒 Purchase Order Management

The application supports a complete purchase-order lifecycle:

```text
Create Purchase Order
        ↓
Add Line Items
        ↓
Order Created
        ↓
Receive Order
        ↓
Inventory Updated
        ↓
Order Marked Received
```

Receiving a purchase order updates the inventory quantities for all associated line items.

The system also prevents an already-received purchase order from being received again.

---

## 🤖 Automatic Reorder Suggestions

When creating a purchase order, the system can generate suggested line items from currently low-stock products.

The workflow is:

```text
Low Stock Product
       ↓
Reorder Candidate
       ↓
Supplier Grouping
       ↓
Purchase Order
       ↓
Receiving
       ↓
Stock Increased
```

This reduces manual inventory calculations and creates a foundation for future demand-based replenishment.

---

## 📊 Inventory Health Reporting

The Operations Console provides a live inventory health view containing metrics such as:

* Total products
* Total units in stock
* Total inventory value
* Number of low-stock products

These values are calculated from the current database state rather than relying on stale cached metrics.

---

## 🖥️ Operations Console

The Streamlit frontend is designed around an operations-focused **master-detail workflow**.

### Main interface capabilities

* Search products
* Filter inventory
* Inspect product details
* Perform quick inventory actions
* Review low-stock products
* Manage purchase orders
* Review inventory reports
* Display loading states
* Display empty states
* Display validation errors
* Display API connectivity failures

The UI communicates with the backend exclusively through REST API requests.

---

# 🏗️ Architecture

The project follows a layered architecture designed to keep business logic independent from HTTP and UI concerns.

```text
┌─────────────────────────────────────────────┐
│           Streamlit Operations Console      │
│                                             │
│ Search • Filters • Details • Actions        │
│ Purchase Orders • Reports                   │
└──────────────────────┬──────────────────────┘
                       │
                       │ HTTP / REST
                       ▼
┌─────────────────────────────────────────────┐
│              FastAPI Application             │
│                                             │
│ Routes • Validation • HTTP Responses        │
│ Error Translation • OpenAPI Documentation   │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│             Inventory Service Layer          │
│                                             │
│ Business Rules • Stock Logic                │
│ Purchase Orders • Reordering                │
│ Inventory Reports                           │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              SQLAlchemy 2.0 ORM             │
│                                             │
│ Models • Relationships • Queries            │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                  SQLite                      │
│                                             │
│ Persistent Inventory Database               │
└─────────────────────────────────────────────┘
```

---

# 🧠 Architectural Principles

## 1. Separation of Concerns

The project deliberately separates:

```text
UI
 ↓
HTTP API
 ↓
Business Logic
 ↓
Persistence
```

The Streamlit application does not contain inventory business rules.

The FastAPI layer does not contain domain logic.

The service layer does not know anything about HTTP or Streamlit.

---

## 2. Service Layer Independence

The central business logic lives in:

```text
src/inventory_service.py
```

The service layer is intentionally independent from HTTP.

It accepts explicit database sessions and works with domain/database objects without knowing whether the caller is:

* FastAPI
* a test
* another application component

This makes the business logic independently testable and reusable.

---

## 3. Thin API Layer

The FastAPI application acts primarily as a translation layer:

```text
HTTP Request
     ↓
Validation
     ↓
Service Layer
     ↓
Business Result
     ↓
HTTP Response
```

Business rules are not duplicated inside route handlers.

---

## 4. Real Client/Server Boundary

The Streamlit frontend communicates with FastAPI using HTTP requests.

```python
requests
    ↓
FastAPI
    ↓
Inventory Service
```

The frontend does **not** directly import:

```text
inventory_service.py
```

This creates a genuine backend/frontend boundary similar to larger full-stack systems.

---

# 💰 Financial Data Design

One important engineering decision is the representation of monetary values.

### ❌ Avoid

```python
unit_price = 12.99
```

Floating-point values can introduce precision issues.

### ✅ Use

```python
unit_price_cents = 1299
```

The system stores the canonical monetary value as an integer.

This provides predictable:

* comparisons
* calculations
* persistence
* serialization

The dollar representation is generated only when required for display.

---

# 🔒 Business Rules

The application enforces important inventory rules.

### Stock cannot become negative

```text
Valid:

10 → 7
7 → 0

Invalid:

7 → -1
```

An insufficient-stock operation raises the appropriate domain exception.

---

### Low-stock boundary is inclusive

If:

```text
Current Stock = Threshold
```

the product is considered low-stock.

For example:

```text
Stock:      10
Threshold:  10

Status: LOW STOCK
```

---

### Purchase orders cannot be received twice

```text
Created
   ↓
Received
   ↓
❌ Receive again
```

The system rejects duplicate receiving operations.

---

### Purchase-order receiving updates all lines

When a purchase order is received, each line item contributes its ordered quantity to inventory.

The operation is treated as a single inventory workflow rather than independent manual updates.

---

# 🧪 Testing & Quality Assurance

The project includes a **43-test automated test suite**:

```text
29 Service-Layer Tests
14 API-Layer Tests
────────────────────
43 Total Tests
```

Run:

```bash
python -m pytest tests/ -v
```

---

## Test Coverage Highlights

The test suite verifies:

### Stock Management

* Increasing stock
* Decreasing stock
* Decreasing stock to zero
* Rejecting negative inventory
* Insufficient stock handling

### Low-Stock Logic

* Exact threshold boundary
* Products below threshold
* Severity ordering
* Worst-shortfall-first behavior

### Purchase Orders

* Creating purchase orders
* Multi-line orders
* Receiving orders
* Inventory updates after receiving
* Preventing duplicate receiving

### API Validation

The HTTP layer verifies correct handling of:

* Duplicate SKUs
* Unknown categories
* Unknown products
* Invalid operations
* Proper HTTP error responses

### Route Safety

The project explicitly tests the relationship between:

```text
/products/low-stock
```

and:

```text
/products/{product_id}
```

to prevent the dynamic route from incorrectly capturing the static endpoint.

---

# 🐛 Engineering Case Study: SQLite Test Isolation

During API testing, an important issue was discovered with SQLite's in-memory database.

The initial testing approach used:

```text
sqlite:///:memory:
```

The problem was that SQLite's in-memory database is connection-scoped.

The application initialization created tables through one connection while the API test requests could use another connection.

Result:

```text
no such table: products
```

### Root Cause

```text
Connection A
   └── creates tables

Connection B
   └── sees a different empty database
```

### Solution

Tests were changed to use a temporary SQLite file created through pytest's `tmp_path`.

This provided:

* isolated test databases
* reliable connection behavior
* reproducible tests
* behavior closer to the application's file-backed runtime

After the fix:

```text
43 tests passed
```

This is a good example of why integration testing can expose problems that unit tests alone may miss.

---

# 🛠️ Technology Stack

| Layer             | Technology                                                        |
| ----------------- | ----------------------------------------------------------------- |
| Language          | Python 3.12                                                       |
| Backend           | FastAPI                                                           |
| ORM               | SQLAlchemy 2.0                                                    |
| Database          | SQLite                                                            |
| Frontend          | Streamlit                                                         |
| Data Processing   | Pandas                                                            |
| HTTP Client       | Requests                                                          |
| Testing           | Pytest                                                            |
| API Testing       | FastAPI TestClient                                                |
| API Documentation | OpenAPI / Swagger                                                 |
| Deployment        | Streamlit Cloud / Render / Vercel-compatible backend architecture |

---

# 📁 Project Structure

```text
inventory-management-system/
│
├── src/
│   ├── config.py
│   ├── exceptions.py
│   ├── models.py
│   ├── database.py
│   └── inventory_service.py
│
├── api/
│   └── main.py
│
├── scripts/
│   └── seed_data.py
│
├── tests/
│   ├── test_inventory_service.py
│   └── test_api.py
│
├── data/
│   └── inventory.db
│
├── app.py
├── requirements.txt
├── vercel.json
├── GUIDE.txt
├── README.md
└── LICENSE
```

### Responsibility Overview

| File                              | Responsibility                       |
| --------------------------------- | ------------------------------------ |
| `src/config.py`                   | Configuration and business constants |
| `src/exceptions.py`               | Domain-specific exception hierarchy  |
| `src/models.py`                   | SQLAlchemy ORM models                |
| `src/database.py`                 | Database engine/session management   |
| `src/inventory_service.py`        | Core business logic                  |
| `api/main.py`                     | FastAPI REST endpoints               |
| `app.py`                          | Streamlit Operations Console         |
| `scripts/seed_data.py`            | Realistic demo data generation       |
| `tests/test_inventory_service.py` | Service-layer tests                  |
| `tests/test_api.py`               | HTTP/API integration tests           |

---

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone <YOUR-REPOSITORY-URL>
cd inventory-management-system
```

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🌱 Seed Demo Data

Populate the database with realistic inventory data:

```bash
python scripts/seed_data.py
```

This creates a useful demo environment containing products, suppliers, categories, and inventory conditions.

---

# ▶️ Run the Application

The application consists of two processes:

```text
FastAPI Backend
+
Streamlit Frontend
```

## Terminal 1 — Start FastAPI

```bash
uvicorn api.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

---

## 📚 API Documentation

FastAPI automatically provides interactive API documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

## Terminal 2 — Start Streamlit

```bash
streamlit run app.py
```

The browser will open the Operations Console.

---

# 🔌 API Architecture

The backend exposes REST endpoints for inventory operations.

Conceptually:

```text
Products
 ├── List products
 ├── Retrieve product
 ├── Create product
 ├── Update stock
 └── Detect low-stock products

Purchase Orders
 ├── Create order
 ├── Add line items
 ├── Receive order
 └── Prevent duplicate receiving

Reports
 └── Generate current inventory health metrics
```

FastAPI also provides machine-readable OpenAPI documentation automatically.

---

# 🚀 Deployment

Because the system consists of two services, deployment should account for their different runtime requirements.

## Frontend — Streamlit

Recommended options include:

* Streamlit Community Cloud
* Render
* Hugging Face Spaces

The frontend requires a persistent process capable of serving the Streamlit application.

Configure the deployed frontend to communicate with the deployed FastAPI backend through the backend URL.

---

# ☁️ Backend — FastAPI

FastAPI can be deployed to serverless platforms such as Vercel.

However, there is an important database consideration.

### SQLite + Serverless

SQLite is file-based.

Serverless environments may have ephemeral filesystems, meaning local database writes should not be treated as durable production persistence.

Therefore:

```text
Local Development
      ↓
SQLite
```

is appropriate for development and demonstration.

For a persistent cloud deployment:

```text
FastAPI
   ↓
SQLAlchemy
   ↓
Hosted PostgreSQL
```

is the recommended architecture.

Potential PostgreSQL providers include services such as Neon or Supabase.

The SQLAlchemy model layer is designed so that moving away from SQLite primarily requires changing the database connection configuration rather than rewriting the business logic.

---

# 🧩 Recommended Production Deployment

For a more production-oriented deployment:

```text
                 ┌──────────────────────┐
                 │   Streamlit Cloud    │
                 │   Operations Console │
                 └──────────┬───────────┘
                            │
                            │ HTTPS
                            ▼
                 ┌──────────────────────┐
                 │     FastAPI API      │
                 │       Backend       │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │      PostgreSQL      │
                 │   Persistent Data    │
                 └──────────────────────┘
```

This removes the persistence limitations associated with using SQLite in a serverless environment.

---

# 📈 Performance & Scalability Considerations

The current architecture is intentionally designed so that future improvements can be introduced without rewriting the entire application.

### Current

```text
Streamlit
   ↓
FastAPI
   ↓
Service Layer
   ↓
SQLAlchemy
   ↓
SQLite
```

### Future

```text
Web / Mobile Clients
        ↓
   API Gateway
        ↓
     FastAPI
        ↓
 Service Layer
        ↓
 SQLAlchemy
        ↓
 PostgreSQL
```

Potential future additions include:

* Redis caching
* Background workers
* asynchronous tasks
* centralized authentication
* observability
* database migrations
* horizontal API scaling

---

# 🗺️ Roadmap — Version 2.0

The following features are planned but are **not represented as implemented functionality in the current release**.

## 🔐 Authentication & Authorization

* User authentication
* Role-based access control
* Warehouse staff roles
* Manager roles
* Permission-based operations

---

## 🗄️ PostgreSQL

Replace SQLite with hosted PostgreSQL for persistent cloud deployment.

---

## 📷 Barcode & SKU Scanning

Add camera-based barcode/SKU scanning to speed up warehouse operations.

---

## 📧 Automated Supplier Notifications

Automatically send purchase-order notifications to supplier contacts after order creation.

---

## 📊 Historical Inventory Analytics

Track inventory snapshots over time and visualize:

* Stock trends
* Reorder frequency
* Product movement
* Inventory valuation
* Stockout history

---

## 🏢 Multi-Warehouse Support

Extend the data model from:

```text
Global Stock
```

to:

```text
Warehouse A
 ├── Product A
 └── Product B

Warehouse B
 ├── Product A
 └── Product C
```

This would enable location-specific inventory management.

---

# 🔭 Future AI Opportunities

The current rule-based reorder system provides a strong foundation for future machine-learning capabilities.

Possible AI extensions include:

### Demand Forecasting

Predict future product demand from historical sales data.

### Intelligent Reordering

Instead of:

```text
IF stock <= threshold
```

use:

```text
Forecasted Demand
+
Lead Time
+
Safety Stock
=
Recommended Order Quantity
```

### Anomaly Detection

Identify unusual inventory behavior such as:

* unexpected stock decreases
* abnormal order frequency
* suspicious inventory adjustments
* unusual supplier patterns

### Predictive Stockout Detection

Estimate the probability of a future stockout before inventory reaches the configured threshold.

---

# 💡 Key Engineering Decisions

## Integer Currency Representation

Avoid floating-point financial calculations by storing prices as integer cents.

## Layered Architecture

Keep business logic independent from HTTP and UI frameworks.

## Real HTTP Communication

Make the Streamlit frontend consume the FastAPI backend through actual REST requests.

## Domain Exceptions

Use custom exceptions to represent business-rule failures clearly.

## Automated Testing

Test both:

```text
Business Logic
+
Real HTTP API
```

rather than relying only on isolated unit tests.

## Explicit Database Sessions

Pass database sessions into service functions rather than hiding persistence state inside business logic.

## Realistic Seed Data

Provide a reproducible demo dataset so the application can be evaluated immediately after setup.

---

# 🏆 Why This Project Matters

This project demonstrates more than basic Python CRUD development.

It demonstrates practical software-engineering concepts including:

* REST API development
* Layered architecture
* Service-oriented design
* ORM-based persistence
* Database modeling
* Business-rule enforcement
* Financial data integrity
* Client-server communication
* Automated testing
* Integration testing
* Error handling
* API documentation
* Deployment architecture
* Production trade-off analysis
* Scalable application design

The result is a foundation that can evolve from a local inventory application into a cloud-hosted business platform.

---

# 📊 Project Quality Snapshot

| Area               | Implementation             |
| ------------------ | -------------------------- |
| Backend API        | FastAPI REST               |
| Database Layer     | SQLAlchemy 2.0             |
| Frontend           | Streamlit                  |
| Architecture       | Layered / Service-based    |
| HTTP Boundary      | Real REST communication    |
| Automated Tests    | 43                         |
| Service Tests      | 29                         |
| API Tests          | 14                         |
| API Documentation  | OpenAPI / Swagger          |
| Demo Data          | Automated seeding          |
| Currency Safety    | Integer cents              |
| Error Handling     | Custom exception hierarchy |
| Cloud Architecture | Deployment-ready           |
| Future Database    | PostgreSQL-ready           |

---

# 👨‍💻 Author

**Sumair Ahmed Dero**

BS Artificial Intelligence Student
University of Sindh, Jamshoro

Focused on building practical systems across:

* Artificial Intelligence
* Machine Learning
* Backend Engineering
* Full-Stack Development
* Robotics
* AI Research

This project is part of my professional software engineering and AI portfolio, with an emphasis on clean architecture, real-world problem solving, testing, and production-oriented development.

---

# 🤝 Contributing

Contributions are welcome.

## Development Workflow

```bash
git checkout -b feature/your-feature
```

Implement the change while following the existing architectural boundaries.

Business rules should remain inside:

```text
src/inventory_service.py
```

rather than being duplicated inside:

```text
api/main.py
```

Add or update tests for new behavior.

Run:

```bash
python -m pytest tests/ -v
```

Commit your changes and open a pull request.

---

# 📜 License

This project is licensed under the **MIT License**.

See the `LICENSE` file for complete license information.

---

# ⭐ Final Note

If you find this project useful or interesting, consider starring the repository.

The project is intentionally designed around a simple principle:

> **Build software that solves a real operational problem, enforce its business rules explicitly, test the critical workflows, and design the architecture so it can grow.**

---
