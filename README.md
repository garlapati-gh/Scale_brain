# ScaleScope | AI-Powered Operations Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.64.0-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-In--Memory%20OLAP-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![OpenAI / OpenRouter](https://img.shields.io/badge/LLM-OpenRouter%20%2F%20GPT--4o--mini-74aa9c?logo=openai&logoColor=white)](https://openrouter.ai/)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed%20(Pytest)-brightgreen?logo=pytest&logoColor=white)](tests/)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=github-actions&logoColor=white)](.github/workflows/python.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **ScaleScope** is an enterprise-grade operations intelligence and natural-language analytics platform. It empowers operations leaders and engineering teams to query operational datasets in plain English, generating performant, safe SQL queries and rendering interactive KPI visualizations with sub-second latency.

---

## 📌 Executive Summary & Resume Highlights

Built to bridge operations telemetry with conversational AI, ScaleScope addresses the latency and complexity of querying multi-table operational databases:

* **Natural Language to SQL Engine:** Translates complex analytical questions into clean, single-statement SQLite SELECT queries powered by LLMs (OpenRouter / GPT-4o-mini).
* **Strict SQL Security Guardrails:** Implements a multi-layered security model using SQLite's native C-level authorizer (`set_authorizer`), blocking all DDL/DML mutations (`INSERT`, `UPDATE`, `DELETE`, `DROP`), enforcing table whitelists, and rejecting file I/O or extension loads.
* **Deterministic Synthetic Telemetry:** Generates reproducible, realistic operational datasets (12 projects, 18 cross-functional workers, 700 tasks, and quality reviews) with foreign-key referential integrity.
* **Thread-Safe State & Concurrency:** Employs reentrant locking (`RLock`) to guarantee thread-safe operations during concurrent Streamlit query execution against shared in-memory SQLite connections.
* **Production Engineering Standards:** Fully tested with **Pytest** (19 unit & integration tests), linted with **Flake8**, and verified with **GitHub Actions CI** across Python 3.11, 3.12, and 3.13.

---

## 🏛️ System Architecture

ScaleScope decouples the user experience, language model query translation, security verification, and analytical storage:

```mermaid
flowchart TD
    User([Operations User / Analyst]) -->|Plain English Question| UI[Streamlit Interactive Dashboard]
    UI -->|Telemetry Request| Engine[Query Engine]
    
    subgraph AI Translation Layer
        Engine -->|Prompt + Schema Constraints| LLM[OpenRouter / OpenAI LLM]
        LLM -->|Generated SQL Statement| Parser[SQL Sanitizer & Cleaner]
    end

    subgraph Security & Execution Guardrails
        Parser -->|Regex Pre-flight Check| Preflight{Single SELECT/WITH?}
        Preflight -- No --> Error[QueryError Rejection]
        Preflight -- Yes --> Auth[SQLite Custom Authorizer]
        Auth -->|Verify Table Whitelist & Deny DDL/DML| PermCheck{Authorized?}
        PermCheck -- Denied --> Error
        PermCheck -- Approved --> DB[(In-Memory SQLite OLAP Store)]
    end

    DB -->|Fetch Clean Result Set (Max 250 Rows)| Pandas[Pandas DataFrame]
    Pandas -->|Auto-Render Metric & Charts| Plotly[Plotly Visualizations]
    Plotly --> UI
    Pandas --> UI
```

### Flow Breakdown

1. **User Interface:** Clean Streamlit dashboard rendering live executive KPIs (task backlogs, completion velocity, quality rubrics) and an intuitive natural language inquiry portal.
2. **AI Translation:** Injects strict relational schema boundaries into system prompts, producing single SQLite queries without markdown or conversational filler.
3. **Security Firewall:**
   - **Pre-flight Regex:** Enforces `SELECT` / `WITH` statement prefixes and prohibits stacked queries (semicolon splitting).
   - **SQLite Authorizer (`_authorize`):** Intercepts low-level SQLite execution actions. Restricts table reads exclusively to `projects`, `workers`, `tasks`, and `reviews`. Blocks access to system catalog tables (`sqlite_master`) and malicious functions (`load_extension`, `readfile`, `writefile`).
4. **Data Delivery:** Caps queries at 250 rows to protect memory limits, converts results into typed `pd.DataFrame`s, and automatically generates interactive Plotly charts when aggregations are detected.

---

## 📊 Interactive Dashboard Features

| Feature | Description |
| :--- | :--- |
| **Live Pulse Metrics** | Tracks real-time operational health: Total Tasks, Completed Tasks, Past Due Backlog, Average Quality Score, and Active Projects. |
| **Workload Distribution** | Visual breakdown of task statuses (`completed`, `in_progress`, `queued`, `blocked`) with consistent semantic color coding. |
| **Completion Velocity** | Area chart plotting historical weekly task completion trends across rolling 12-week windows. |
| **Natural Language Querying** | Accepts conversational inquiries (e.g., *"Which projects have the most overdue tasks?"*) and executes validated SQL queries. |
| **Dynamic Visualizer** | Automatically parses query results; if numeric and categorical columns are present, generates interactive bar charts alongside the raw tabular data. |
| **SQL Transparency** | Expandable code inspector showing the generated SQL query for full operational auditability. |

---

## 🛠️ Tech Stack

* **Language:** Python 3.11+
* **Framework:** [Streamlit](https://streamlit.io/) (Web application & responsive layout)
* **Visualization:** [Plotly Express](https://plotly.com/python/) (Interactive chart components)
* **Data Processing:** [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/)
* **Database:** SQLite3 (In-memory relational store with foreign key enforcement)
* **LLM Orchestration:** [OpenAI Python SDK](https://github.com/openai/openai-python) via [OpenRouter](https://openrouter.ai/)
* **Testing & Quality:** Pytest, Flake8, GitHub Actions CI

---

## 📂 Project Structure

```text
ScaleScope/
├── .github/
│   └── workflows/
│       └── python.yml          # GitHub Actions CI matrix (Python 3.11, 3.12, 3.13)
├── scalescope/
│   ├── .env                    # Local secrets (git-ignored)
│   ├── .env.example            # Environment template for developers
│   ├── .gitignore              # Component-level ignore rules
│   ├── app.py                  # Streamlit application UI & dashboard logic
│   ├── database.py             # SQLite schema, seed generator & data layer
│   ├── query_engine.py         # Text-to-SQL compiler & read-only authorizer
│   └── requirements.txt        # Pinned dependency manifest
├── tests/
│   ├── __init__.py             # Test package initialization
│   ├── test_database.py        # Database schema, foreign keys & seeding tests
│   └── test_query_engine.py    # Query engine, authorizer security & LLM mock tests
├── .env.example                # Root environment template
├── .gitignore                  # Root gitignore (prevents .venv, secrets, cache leaks)
├── LICENSE                     # MIT License
├── pytest.ini                  # Pytest configuration and path resolution
├── README.md                   # Comprehensive platform documentation
└── requirements.txt            # Root pinned dependency manifest
```

---

## 🚀 Quick Start & Installation

### Prerequisites

* Python 3.11, 3.12, or 3.13 installed
* An [OpenRouter API Key](https://openrouter.ai/keys) (or OpenAI-compatible API key)

### 1. Clone the Repository

```bash
git clone https://github.com/garlapati-gh/Scale_brain.git
cd Scale_brain
```

### 2. Create and Activate a Virtual Environment

```bash
# On macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

# On Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and insert your OpenRouter API key:

```bash
# On macOS / Linux:
cp .env.example .env

# On Windows (PowerShell):
copy .env.example .env
```

Edit `.env`:
```ini
OPENROUTER_API_KEY=sk-or-v1-your-actual-api-key-here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

### 5. Launch the Dashboard

```bash
streamlit run scalescope/app.py
```

Open your browser to `http://localhost:8501` to explore the dashboard.

---

## 🧪 Testing & Code Quality

ScaleScope includes an extensive test suite verifying database integrity, seed reproducibility, SQL injection protection, and API parsing.

### Run Unit & Integration Tests

```bash
pytest -v
```

Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
collected 19 items

tests/test_database.py::TestDatabase::test_create_database_connection PASSED [  5%]
tests/test_database.py::TestDatabase::test_database_tables_exist PASSED      [ 10%]
tests/test_database.py::TestDatabase::test_database_seeded_row_counts PASSED [ 15%]
tests/test_database.py::TestDatabase::test_read_frame_returns_dataframe PASSED [ 21%]
tests/test_database.py::TestDatabase::test_data_integrity PASSED             [ 26%]
tests/test_database.py::TestDatabase::test_database_deterministic_seeding PASSED [ 31%]
tests/test_database.py::TestDatabase::test_foreign_key_enforcement PASSED   [ 36%]
tests/test_query_engine.py::TestQueryEngine::test_is_configured PASSED       [ 42%]
tests/test_query_engine.py::TestQueryEngine::test_execute_readonly_valid_select PASSED [ 47%]
tests/test_query_engine.py::TestQueryEngine::test_execute_readonly_cte_query PASSED [ 52%]
tests/test_query_engine.py::TestQueryEngine::test_execute_readonly_blocks_dml PASSED [ 57%]
tests/test_query_engine.py::TestQueryEngine::test_execute_readonly_blocks_ddl PASSED [ 63%]
tests/test_query_engine.py::TestQueryEngine::test_execute_readonly_blocks_multiple_statements PASSED [ 68%]
tests/test_query_engine.py::TestQueryEngine::test_execute_readonly_enforces_allowed_tables PASSED [ 73%]
tests/test_query_engine.py::TestQueryEngine::test_execute_readonly_caps_max_rows PASSED [ 78%]
tests/test_query_engine.py::TestQueryEngine::test_generate_sql_missing_api_key PASSED [ 84%]
tests/test_query_engine.py::TestQueryEngine::test_generate_sql_empty_question PASSED [ 89%]
tests/test_query_engine.py::TestQueryEngine::test_generate_sql_cleans_markdown PASSED [ 94%]
tests/test_query_engine.py::TestQueryEngine::test_ask_integration_flow PASSED [100%]

============================= 19 passed in 5.80s ==============================
```

### Run Linter

```bash
flake8 . --count --max-line-length=127 --statistics
```

---

## 🔒 Security & Query Sandboxing

Executing AI-generated SQL queries on production databases introduces substantial injection and data alteration risks. ScaleScope mitigates these vulnerabilities at multiple depths:

1. **Native SQLite Authorizer (`sqlite3.set_authorizer`):**
   - Intercepts SQL engine parsing at the engine bytecode level.
   - Denies any action except `SQLITE_SELECT` and `SQLITE_READ` on `ALLOWED_TABLES` (`projects`, `workers`, `tasks`, `reviews`).
   - Automatically returns `SQLITE_DENY` if the query attempts to read tables outside the whitelist or internal schemas (`sqlite_master`).
2. **Regex AST Sanitation:**
   - Enforces queries starting with `SELECT` or `WITH`.
   - Disallows statement chaining by rejecting inputs containing semicolons `;`.
3. **Denial of Dangerous Built-in Functions:**
   - Blocks unsafe native extensions including `load_extension`, `writefile`, and `readfile`.
4. **Denial-of-Service Prevention:**
   - Enforces a strict upper bound of `MAX_ROWS = 250` per query to protect against unbounded memory consumption.

---

## 🔮 Future Roadmap (FAANG / Production Grade Enhancements)

- [ ] **Role-Based Access Control (RBAC):** Multi-tenant authentication with OAuth2 / Google SSO.
- [ ] **Root-Cause AI Insights ("Why did Project Alpha slow down?"):** Proactive LLM reasoning across task velocity anomalies, worker workload bottlenecks, and rubric review deviations.
- [ ] **Automated Report Export:** One-click automated export to styled CSV, Excel, and PDF executive briefings.
- [ ] **Persistent OLAP Data Connectors:** Support for DuckDB, PostgreSQL, and Snowflake backends via SQLAlchemy.
- [ ] **Conversational Follow-Ups & Memory:** Session-based multi-turn chat allowing users to drill deeper into previous query results.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

