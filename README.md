# AI-Powered Root Cause Analysis Agent

An AI-powered Root Cause Analysis (RCA) system that combines application telemetry, dependency relationships, and Large Language Models (LLMs) to investigate application incidents and generate evidence-based explanations.

The project uses **ClickHouse** for observability data, **Neo4j** for service dependency analysis, and a **Python-based AI agent** to coordinate investigation and explain potential root causes.

---

## 1. Project Overview

Modern distributed applications generate large volumes of logs, traces, and metrics. When an incident occurs, engineers often need to inspect multiple services and data sources manually to understand what happened.

This project explores how an AI agent can assist engineers by:

* Investigating application errors and telemetry.
* Identifying affected services.
* Exploring service dependencies.
* Correlating observations across different data sources.
* Producing a structured Root Cause Analysis report.

### Project Objective

Build an AI assistant that helps engineers answer:

1. What happened?
2. Which service is experiencing the issue?
3. What evidence supports the investigation?
4. Which dependent services may be involved?
5. What is the likely root cause?
6. What should be investigated next?

---

## 2. Technology Stack

| Component              | Technology         | Purpose                                  |
| ---------------------- | ------------------ | ---------------------------------------- |
| Programming Language   | Python             | Agent implementation                     |
| Observability Database | ClickHouse         | Logs, traces, and metrics                |
| Graph Database         | Neo4j              | Service dependency relationships         |
| AI Model               | Groq-hosted LLM    | Natural-language reasoning               |
| Telemetry              | OpenTelemetry Demo | Sample distributed application telemetry |
| Containerization       | Docker Compose     | Local infrastructure                     |
| Interface              | Python CLI         | Engineer interaction                     |

---

## 3. System Architecture

The application follows a multi-source investigation architecture.

```text
             ENGINEER
                |
                v
        Python CLI Interface
                |
                v
        AI Root Cause Agent
                |
       +--------+--------+
       |                 |
       v                 v
   ClickHouse          Neo4j
       |                 |
       v                 v
 Logs / Traces /     Service Dependency
 Metrics             Relationships
       |                 |
       +--------+--------+
                |
                v
       Evidence Collection
                |
                v
       AI-Assisted Analysis
                |
                v
       Structured RCA Report
```

### Component Responsibilities

**Python Agent**

Receives the engineer's question, coordinates investigation, retrieves relevant evidence, and generates an explanation.

**ClickHouse**

Stores and provides access to application telemetry, including logs, traces, and metrics.

**Neo4j**

Represents relationships between microservices and helps investigate upstream and downstream dependencies.

**LLM**

Interprets collected evidence and generates a human-readable investigation summary.

---

## 4. Key Capabilities

### 4.1 Telemetry Investigation

The agent can investigate application telemetry stored in ClickHouse.

Relevant data includes:

* Application logs
* Distributed traces
* Service-level metrics
* Error events
* Performance observations

### 4.2 Service Dependency Analysis

Neo4j represents relationships between application services.

Example dependency structure:

```text
Frontend
   |
   v
Checkout
   |
   +------> Payment
   |           |
   |           v
   |      Visa Validation
   |
   +------> Email
   |
   +------> Shipping
```

This allows an investigation to consider dependencies rather than examining an isolated service.

### 4.3 AI-Assisted Root Cause Analysis

The agent combines retrieved observations with service relationships to produce an explanation.

The output is intended to distinguish:

* Observed evidence
* Potential causes
* Supporting observations
* Unverified assumptions
* Suggested investigation steps

---

## 5. Example Use Case

### Scenario: Payment Failure

An engineer observes that customers are experiencing failures during checkout.

The investigation can follow this sequence:

1. Identify payment-related errors in application logs.
2. Examine relevant traces to understand the request path.
3. Inspect payment service dependencies using Neo4j.
4. Correlate telemetry observations.
5. Generate an RCA explanation based on the collected evidence.

The project includes an example involving a payment validation error:

`Visa cache full: cannot add new item.`

This example demonstrates how telemetry and dependency information can support incident investigation.

The exact underlying cause and customer impact require further verification from operational evidence.

---

## 6. Repository Structure

```text
ai-root-cause-agent/
│
├── agent/
│   ├── rca_agent.py
│   ├── cli_agent.py
│   ├── evidence_collector.py
│   ├── offline_rca.py
│   ├── clickhouse_tool.py
│   ├── neo4j_tool.py
│   ├── rca_workflow.py
│   ├── evidence.json
│   ├── rca_report.txt
│   ├── .env.example
│   └── ...
│
├── clickhouse/
│
├── neo4j/
│   └── init.cypher
│
├── docs/
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 7. Getting Started

### Prerequisites

* Python 3.11 or later
* Docker Desktop or Docker Engine
* Git
* ClickHouse
* Neo4j
* Groq API key for LLM-based execution

### Step 1: Clone the Repository

```bash
git clone git@github.com:Aktreides44/ai-root-cause-agent.git

cd ai-root-cause-agent
```

### Step 2: Create a Python Virtual Environment

```bash
python3 -m venv agent/.venv
```

Activate it on Linux or WSL:

```bash
source agent/.venv/bin/activate
```

### Step 3: Install Dependencies

Install the Python packages required by the agent.


### Step 4: Configure Environment Variables

Create a local `.env` file using the provided example:

```bash
cp agent/.env.example agent/.env
```

Configure the required credentials and connection settings in `agent/.env`.

**Never commit `.env` or API keys to GitHub.**

### Step 5: Start Infrastructure

From the project root:

```bash
docker compose up -d
```

Check running containers:

```bash
docker compose ps
```

### Step 6: Run the Agent

The repository includes Python CLI and investigation scripts under `agent/`.

Run the appropriate entry point after configuring the environment.

---

## 8. Project Status

This project is an internship development and experimentation project.

| Area                        | Status                              |
| --------------------------- | ----------------------------------- |
| Python agent implementation | In development                      |
| ClickHouse integration      | Implemented for local investigation |
| Neo4j dependency analysis   | Implemented for local investigation |
| Telemetry investigation     | Tested with sample data             |
| AI-assisted RCA             | Experimental                        |
| Production deployment       | Not yet validated                   |

---

## 9. Current Limitations

* The system is tested against a local demonstration environment.
* Findings depend on the completeness and quality of available telemetry.
* An LLM-generated explanation is not automatically a verified root cause.
* Customer impact and production reliability have not been independently validated.
* Model API rate limits may affect investigation execution.

---

## 10. Future Enhancements

* Improve automated correlation of logs, traces, and metrics.
* Add stronger evidence validation and confidence reporting.
* Improve handling of large telemetry datasets.
* Add incident severity and impact assessment.
* Integrate with an observability dashboard.
* Expand testing against additional failure scenarios.
* Develop a more interactive engineer-facing interface.

---

## 11. Author

**Project:** AI-Powered Root Cause Analysis Agent
**Repository:** [ai-root-cause-agent](https://github.com/Aktreides44/ai-root-cause-agent)

Developed as part of an internship project exploring AI agents, observability, graph databases, and automated incident investigation.
