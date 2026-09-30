import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import clickhouse_connect
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent / ".env")


# ---------------------------------------------------------
# ClickHouse
# ---------------------------------------------------------

clickhouse = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST"),
    port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
    username=os.getenv("CLICKHOUSE_USER"),
    password=os.getenv("CLICKHOUSE_PASSWORD"),
    database=os.getenv("CLICKHOUSE_DATABASE", "default"),
)


def query_clickhouse(sql: str):
    result = clickhouse.query(sql)

    columns = result.column_names

    return [
        dict(zip(columns, row))
        for row in result.result_rows
    ]


# ---------------------------------------------------------
# Neo4j
# ---------------------------------------------------------

neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USER"),
        os.getenv("NEO4J_PASSWORD"),
    ),
)


def get_dependencies(service: str):
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (s:Service {name: $service})-[r]->(d:Service)
            RETURN
                s.name AS service,
                type(r) AS relationship,
                d.name AS dependency
            ORDER BY dependency
            """,
            service=service,
        )

        return [dict(row) for row in result]


# ---------------------------------------------------------
# LLM
# ---------------------------------------------------------

llm = OpenAI(
    base_url=os.getenv("LOCALAI_BASE_URL"),
    api_key=os.getenv("LOCALAI_API_KEY") or "not-needed",
)

MODEL = os.getenv("LOCALAI_MODEL", "qwen3-4b")


# ---------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "query_clickhouse",
            "description": (
                "Run a read-only SQL query against the ClickHouse "
                "observability database. Use this to investigate "
                "logs, traces, and metrics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Read-only ClickHouse SQL query."
                    }
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dependencies",
            "description": (
                "Get service dependencies and relationships from "
                "the Neo4j service topology graph."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name."
                    }
                },
                "required": ["service"],
            },
        },
    },
]


# ---------------------------------------------------------
# Tool execution
# ---------------------------------------------------------

def execute_tool(name, arguments):

    if name == "query_clickhouse":
        return query_clickhouse(arguments["sql"])

    if name == "get_dependencies":
        return get_dependencies(arguments["service"])

    raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------
# Agent
# ---------------------------------------------------------

SYSTEM_PROMPT = """
You are an AI Root Cause Analysis Agent.

Investigate production incidents using evidence.

You have two sources:

1. ClickHouse
   - logs
   - traces
   - metrics

2. Neo4j
   - service dependencies
   - service relationships

Do not invent evidence.

Distinguish clearly between:
- Observed facts
- Reasonable inferences
- Unknown information

For an RCA investigation, gather independent evidence from:
- relevant error logs
- relevant failed traces
- relevant metrics
- relevant service dependencies

Once these evidence categories provide a consistent explanation,
STOP investigating and produce the RCA.

Final response format:

1. Executive Summary
2. Root Cause
3. Evidence
4. Service Dependency and Failure Propagation
5. Customer / Business Impact
6. Confidence
7. Recommended Next Actions
"""


def run_agent(question):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    for round_number in range(8):

        print(f"\n[AGENT ROUND {round_number + 1}]")

        response = llm.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=1000,
        )

        message = response.choices[0].message

        # No more tool calls → final answer
        if not message.tool_calls:
            print("\n=== ROOT CAUSE ANALYSIS ===\n")
            print(message.content)
            return

        messages.append(message)

        for tool_call in message.tool_calls:

            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            print(f"[TOOL] {name}")
            print(f"[ARGS] {arguments}")

            result = execute_tool(name, arguments)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result,
                        default=str,
                    ),
                }
            )

    print("\nAgent stopped after maximum tool rounds.")


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

if __name__ == "__main__":

    question = input(
        "\nDescribe the incident you want to investigate:\n> "
    )

    try:
        run_agent(question)

    finally:
        neo4j_driver.close()
