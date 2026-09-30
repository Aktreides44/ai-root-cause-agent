import json
import os

from dotenv import load_dotenv
from groq import Groq

from cli_agent_backup import query_clickhouse, get_dependencies, neo4j_driver


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv("agent/.env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not configured in agent/.env"
    )

client = Groq(api_key=GROQ_API_KEY)


# ============================================================
# TOOLS
# ============================================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "query_clickhouse",
            "description": (
                "Run a READ-ONLY SQL query against the ClickHouse "
                "observability database. Use this for logs, traces, "
                "metrics, tables, schemas, and other observability "
                "information. Allowed commands are SELECT, SHOW, "
                "and DESCRIBE only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": (
                            "A read-only ClickHouse SQL query. "
                            "Allowed statements: SELECT, SHOW, DESCRIBE."
                        ),
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
                "Retrieve service dependencies and relationships "
                "from the Neo4j service topology graph."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": (
                            "Name of the service whose dependencies "
                            "should be investigated."
                        ),
                    }
                },
                "required": ["service"],
            },
        },
    },
]


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an AI Root Cause Analysis Agent operating through
a command-line interface.

Your job is to help investigate an application and its
observability data.

============================================================
AVAILABLE SYSTEMS
============================================================

1. CLICKHOUSE

ClickHouse contains observability data:

- Logs
- Traces
- Metrics

Use the query_clickhouse tool to investigate:

- Errors
- Application events
- Failed requests
- Traces
- Metrics
- Database tables
- Database schemas

Only use READ-ONLY queries.

Allowed:

- SELECT
- SHOW
- DESCRIBE

Never attempt:

- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- TRUNCATE
- CREATE

============================================================

2. NEO4J

Neo4j contains the service dependency graph.

Use get_dependencies to understand:

- Which services call other services
- Which services depend on other services
- How failures may propagate

============================================================
GENERAL QUESTIONS
============================================================

The user may ask normal questions such as:

"List all tables."

"Show me the latest payment errors."

"What metrics are available?"

"What services does payment depend on?"

For these questions, answer directly using the appropriate
tools.

Do NOT produce a full RCA report unless the user is actually
asking for an investigation or root cause analysis.

============================================================
ROOT CAUSE INVESTIGATION
============================================================

If the user asks you to investigate an incident or determine
a root cause, investigate systematically.

Prefer evidence from:

1. Relevant error logs
2. Relevant failed traces
3. Relevant metrics
4. Relevant service dependencies

Correlate the evidence before reaching a conclusion.

Stop investigating once sufficient independent evidence
supports a consistent explanation.

Do not repeatedly query the same information.

============================================================
EVIDENCE RULES
============================================================

NEVER invent evidence.

Clearly distinguish between:

OBSERVED FACT
Something directly found in logs, traces, metrics,
or Neo4j.

INFERENCE
A reasonable conclusion derived from multiple observed facts.

UNKNOWN
Something that cannot be established from the available data.

Do not present an inference as an observed fact.

============================================================
RCA RESPONSE FORMAT
============================================================

When performing an RCA investigation, use:

1. Executive Summary

2. Root Cause

3. Evidence

4. Service Dependency and Failure Propagation

5. Customer / Business Impact

6. Confidence

7. Recommended Next Actions

Do not invent customer counts, revenue impact,
or other business metrics.

If the available data does not provide them,
explicitly say so.

============================================================
IMPORTANT
============================================================

You are an evidence-driven investigation agent.

Use the available tools rather than guessing.

The objective is not to produce the longest answer.

The objective is to produce the most defensible answer
supported by the available evidence.
"""


# ============================================================
# TOOL EXECUTION
# ============================================================

def execute_tool(name, arguments):

    if name == "query_clickhouse":

        sql = arguments.get("sql", "").strip()

        if not sql:
            raise ValueError("SQL query cannot be empty.")

        normalized = sql.lower()

        allowed = (
            normalized.startswith("select")
            or normalized.startswith("show")
            or normalized.startswith("describe")
        )

        if not allowed:
            raise ValueError(
                "Only SELECT, SHOW, and DESCRIBE queries are allowed."
            )

        return query_clickhouse(sql)

    if name == "get_dependencies":

        service = arguments.get("service", "").strip()

        if not service:
            raise ValueError(
                "Service name cannot be empty."
            )

        return get_dependencies(service)

    raise ValueError(
        f"Unknown tool: {name}"
    )


# ============================================================
# AGENT LOOP
# ============================================================

def run_agent(messages):

    max_rounds = 8

    for round_number in range(max_rounds):

        print()
        print(
            f"[AGENT ROUND {round_number + 1}]"
        )

        try:

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=2000,
            )

        except Exception as error:

            print()
            print("LLM ERROR")
            print("-" * 60)
            print(error)
            print()

            return

        message = response.choices[0].message

        # ----------------------------------------------------
        # FINAL ANSWER
        # ----------------------------------------------------

        if not message.tool_calls:

            print()
            print("=" * 70)
            print("ASSISTANT")
            print("=" * 70)
            print()

            if message.content:
                print(message.content)
            else:
                print("No response was returned.")

            return

        # ----------------------------------------------------
        # TOOL CALLS
        # ----------------------------------------------------

        messages.append(
            message.model_dump()
        )

        for tool_call in message.tool_calls:

            name = tool_call.function.name

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )
            except json.JSONDecodeError:

                arguments = {}

            print()
            print(
                f"[TOOL] {name}"
            )

            print(
                f"[ARGS] {arguments}"
            )

            try:

                result = execute_tool(
                    name,
                    arguments,
                )

                if isinstance(result, list):

                    print(
                        f"[RESULT] {len(result)} records"
                    )

                else:

                    print(
                        "[RESULT] received"
                    )

            except Exception as error:

                print(
                    f"[TOOL ERROR] {error}"
                )

                result = {
                    "error": str(error)
                }

            # ------------------------------------------------
            # RETURN TOOL RESULT TO LLM
            # ------------------------------------------------

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

    print()
    print(
        "Agent stopped after maximum investigation rounds."
    )


# ============================================================
# INTERACTIVE CLI
# ============================================================

def main():

    print()
    print("=" * 70)
    print("AI ROOT CAUSE ANALYSIS AGENT")
    print("=" * 70)
    print()
    print(f"Model: {GROQ_MODEL}")
    print("Backend: Groq")
    print()
    print(
        "Type your question or type 'exit' to quit."
    )
    print()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    while True:

        try:

            question = input("> ").strip()

        except KeyboardInterrupt:

            print("\n")
            print("Exiting...")
            break

        except EOFError:

            print("\n")
            print("Exiting...")
            break

        if not question:
            continue

        if question.lower() in (
            "exit",
            "quit",
        ):
            print()
            print("Goodbye.")
            break

        # Add user message to conversation
        messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        # Run agent
        run_agent(messages)

        print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    finally:

        try:
            neo4j_driver.close()
        except Exception:
            pass