# AI-Powered Root Cause Analysis Agent

An AI-powered incident investigation agent that combines:

- **ClickHouse** for observability data and analytical queries
- **Neo4j** for service and dependency relationships
- **LibreChat** as the conversational AI interface
- **LLM** for investigation and reasoning
- **Python** for agent tools and orchestration

## Project Goal

Build an AI agent that can investigate incidents in a distributed
microservices environment and identify likely root causes.

The initial use case is based on ClickHouse's Observability use case
and its OpenTelemetry e-commerce demo dataset.

## Architecture

```text
User
  |
  v
LibreChat
  |
  v
AI Agent / LLM
  |
  +--------------------+
  |                    |
  v                    v
ClickHouse            Neo4j
  |                    |
Logs                  Service
Metrics               Dependencies
Traces                Relationships
  |                    |
  +---------+----------+
            |
            v
       Root Cause
        Analysis
