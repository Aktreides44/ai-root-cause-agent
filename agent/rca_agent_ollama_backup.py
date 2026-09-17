import asyncio
import json
import time

from ollama import Client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from neo4j_tool import get_dependencies


OLLAMA_HOST = "http://172.29.160.1:11434"
MODEL = "qwen3:8b"


async def main():

    ollama = Client(host=OLLAMA_HOST)

    server_params = StdioServerParameters(
        command="mcp-clickhouse",
        args=[],
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            # Get MCP tools
            mcp_tools = await session.list_tools()

            print("\n=== MCP TOOLS ===")
            for tool in mcp_tools.tools:
                print("-", tool.name)

            # Convert MCP tools into Ollama tool format
            ollama_tools = []

            for tool in mcp_tools.tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                })

            # Add Neo4j dependency tool
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": "get_dependencies",
                    "description": (
                        "Get the services that a given service calls "
                        "in the Neo4j service dependency graph."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service": {
                                "type": "string",
                                "description": (
                                    "Name of the service, for example "
                                    "checkout or payment."
                                ),
                            }
                        },
                        "required": ["service"],
                    },
                },
            })

            messages = [
                {
                    "role": "system",
                    "content": """
You are an AI Root Cause Analysis agent for an
OpenTelemetry e-commerce application.

Your job is to investigate incidents using real evidence.

You have access to ClickHouse tools.

You also have access to a Neo4j service dependency graph
through the get_dependencies tool.

Use ClickHouse for observability evidence such as:
- logs
- traces
- metrics

Use Neo4j when you need to understand:
- which services a service depends on
- how a failure can propagate between services
- which downstream services may be affected

For RCA, combine ClickHouse evidence with Neo4j dependencies
when useful.

IMPORTANT:
- Never invent tables, columns, metrics, errors, or findings.
- You MUST investigate the incident using actual observability data.
- Prefer run_query for ClickHouse investigation.
- Do NOT repeatedly call list_tables when the schema below is already known.
- Do NOT use SELECT *.
- Always use the exact table and column names provided below.
- Keep queries focused and use LIMIT.
- Do not give the final RCA until you have gathered actual evidence.

KNOWN CLICKHOUSE SCHEMA:

1. Logs:
Table: default.otel_logs

Important columns:
- Timestamp
- ServiceName
- SeverityText
- Body

2. Traces:
Table: default.otel_traces

Important columns:
- Timestamp
- TraceId
- SpanName
- ServiceName
- Duration
- StatusCode
- StatusMessage

3. Gauge metrics:
Table: default.otel_metrics_gauge

Important columns:
- TimeUnix
- ServiceName
- MetricName
- Value
- Attributes

Other available metric tables:
- default.otel_metrics_sum
- default.otel_metrics_histogram

INVESTIGATION PROCESS:

Follow this investigation order for payment-related incidents:

1. Query payment error logs using:
   SELECT
       Timestamp,
       ServiceName,
       SeverityText,
       Body
   FROM default.otel_logs
   WHERE lower(SeverityText) = 'error'
     AND lower(ServiceName) = 'payment'
   ORDER BY Timestamp DESC
   LIMIT 20;

2. Query failed payment traces using:
   SELECT
       Timestamp,
       TraceId,
       SpanName,
       ServiceName,
       Duration,
       StatusCode,
       StatusMessage
   FROM default.otel_traces
   WHERE lower(StatusCode) = 'error'
     AND lower(ServiceName) = 'payment'
   ORDER BY Timestamp DESC
   LIMIT 20;

3. Query the Visa validation cache metric using:
   SELECT
       TimeUnix,
       ServiceName,
       MetricName,
       Value,
       Attributes
   FROM default.otel_metrics_gauge
   WHERE MetricName = 'visa_validation_cache.size'
   ORDER BY TimeUnix DESC
   LIMIT 20;

4. Use the Neo4j get_dependencies tool for the relevant service,
   especially payment or checkout, to understand service relationships.

5. Compare the logs, traces, metrics, and service dependencies.

6. Only then provide the root cause and supporting evidence.

IMPORTANT SQL RULES:

- NEVER use SELECT *.
- StatusCode is a String. Compare it with 'error', not a number.
- ServiceName is a String.
- Use the exact table and column names provided above.
- Do not invent columns.
- Do not repeatedly execute the same query.
- If a query returns useful evidence, move to the next investigation step.
- Do not call list_tables unless a query fails because the schema is genuinely unknown.

The ClickHouse database is "default".
""",
                },
                {
                    "role": "user",
                    "content": "Why are customers unable to complete payments?",
                },
            ]

            print("\n=== AGENT INVESTIGATION ===\n")

            response = ollama.chat(
                model=MODEL,
                messages=messages,
                tools=ollama_tools,
                think=False,
                options={
                    "num_predict": 250
                },
            )

            # Agent loop
            max_tool_rounds = 8
            tool_round = 0

            while response.message.tool_calls and tool_round < max_tool_rounds:

                tool_round += 1

                print(
                    f"\n[TOOL ROUND {tool_round}/{max_tool_rounds}]"
                )

                messages.append(response.message)

                for tool_call in response.message.tool_calls:

                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments

                    print(f"\n[AI TOOL CALL] {tool_name}")
                    print(f"[ARGUMENTS] {tool_args}")

                    # Execute Neo4j tool
                    if tool_name == "get_dependencies":

                        service = tool_args["service"]

                        neo4j_result = get_dependencies(service)

                        tool_output = json.dumps(neo4j_result)

                    # Execute ClickHouse MCP tool
                    else:

                        result = await session.call_tool(
                            tool_name,
                            tool_args,
                        )

                        if result.is_error:
                            tool_output = str(result)
                        else:
                            tool_output = result.content[0].text

                    print("[TOOL RESULT RECEIVED]")

                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": tool_output,
                    })

                # Ask Qwen to reason over the evidence
                response = ollama.chat(
                    model=MODEL,
                    messages=messages,
                    tools=ollama_tools,
                    think=False,
                    options={
                        "num_predict": 250
                    },
                )

            if tool_round >= max_tool_rounds:
                print(
                    "\n[WARNING] Maximum tool rounds reached. "
                    "Stopping investigation."
                )

            print("\n=== ROOT CAUSE ANALYSIS ===\n")
            print(response.message.content)


if __name__ == "__main__":
    asyncio.run(main())
