# AI-Powered Root Cause Analysis Agent

An AI-assisted Root Cause Analysis (RCA) agent that investigates application incidents using observability data from ClickHouse and service dependency information from Neo4j.

The project combines a Python command-line interface, evidence collection, and a Groq-powered language model to help engineers understand errors, trace failure propagation, and generate structured incident analysis.

## Project Overview

The agent is designed to answer questions such as:

- What happened during an application incident?
- Which service reported the error?
- How did the failure propagate between services?
- What evidence is available in logs, traces, metrics, and service dependencies?
- What information is still unknown?
- What should be investigated next?

## Architecture

```text
Engineer
   |
   v
Python CLI Agent
   |
   v
Evidence Collection
   |
   +--------------------+
   |                    |
   v                    v
ClickHouse             Neo4j
Logs                   Service Dependencies
Traces                 Dependency Relationships
Metrics
   |                    |
   +---------+----------+
             |
             v
      Evidence Summary
             |
             v
       Groq LLM
             |
             v
    Root Cause Analysis
             |
             v
       Engineer

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core agent development and CLI interface |
| ClickHouse | Storage and querying of observability data |
| Neo4j | Graph-based service dependency analysis |
| Groq API | Large Language Model for generating RCA responses |
| OpenTelemetry | Application logs, traces, and metrics |
| Docker | Running the supporting infrastructure |
| Python-dotenv | Environment variable and configuration management |
| Git & GitHub | Version control and project management |

## Project Structure

```text
ai-root-cause-agent-cli/
│
├── agent/
│   ├── cli_agent.py
│   ├── rca_agent.py
│   ├── evidence_collector.py
│   ├── offline_rca.py
│   ├── cli_agent_backup.py
│   ├── rca_agent_backup.py
│   ├── test_connections.py
│   ├── test_rca_queries.py
│   ├── evidence.json
│   ├── rca_report.txt
│   └── .env.example
│
├── clickhouse/
├── neo4j/
├── docs/
├── .gitignore
└── README.md