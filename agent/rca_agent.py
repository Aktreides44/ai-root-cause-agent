import asyncio
import json
import time

from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from neo4j_tool import get_dependencies


MODEL = "openai/gpt-oss-120b"


async def main():

    groq = Groq()

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

            # Convert MCP tools into Groq tool format
            groq_tools = []

            for tool in mcp_tools.tools:
                groq_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                })

            # Add Neo4j dependency tool
            groq_tools.append({
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

FINAL RCA RESPONSE REQUIREMENTS:

Your final response must be a detailed, evidence-based incident analysis.

Structure the response using these sections:

1. Executive Summary
   - Explain the problem and the most likely root cause in 2–4 sentences.

2. Root Cause
   - State the specific technical root cause.
   - Do not claim causality unless supported by the evidence.

3. Evidence
   - Logs: quote or summarize the relevant observed errors.
   - Traces: describe relevant failed requests, services, or trace relationships.
   - Metrics: describe relevant metric values, trends, thresholds, or anomalies.
   - Clearly identify which evidence was actually observed.

4. Service Dependency and Failure Propagation
   - Use Neo4j dependency information when relevant.
   - Explain how the failure could propagate between services.
   - Distinguish observed dependencies from inferred propagation.

5. Customer / Business Impact
   - Explain what the technical failure means for the customer or application.

6. Confidence
   - Give High, Medium, or Low confidence.
   - Briefly explain why.

7. Recommended Next Actions
   - Provide practical technical investigation or remediation actions.
   - Do not claim that an action has already been performed unless evidence shows it.

STOPPING CONDITION:

Once you have gathered sufficient independent evidence, STOP investigating
and immediately produce the final RCA.

For a normal incident, the following four evidence categories are sufficient:
1. Relevant error logs
2. Relevant failed traces
3. Relevant metrics or quantitative evidence
4. Relevant service dependency information from Neo4j

Once these four categories have been investigated and they support a
consistent explanation, DO NOT perform additional exploratory queries.
Produce the final RCA immediately.

Do not search for every possible piece of evidence. The goal is to establish
a well-supported root cause, not to exhaust the database.

If a query returns no relevant data, treat that as a finding and do not
repeat the same investigation using alternative queries unless the existing
evidence is insufficient or conflicting.

IMPORTANT:
- A failed or empty exploratory query does NOT prevent you from producing
  the RCA if sufficient evidence has already been gathered.
- If sufficient evidence has been gathered, prioritize producing the final
  RCA over making another tool call.
- Never end the investigation with an empty final response.
- Always provide the best evidence-based RCA possible from the evidence
  already collected.
- If evidence is incomplete, explicitly state what is known, what is inferred,
  and what remains unknown.
IMPORTANT:
- Prefer evidence over speculation.
- Clearly distinguish FACTS observed in telemetry from INFERENCES made from those facts.
- Include specific metric values, error messages, service names, and relationships when they materially support the RCA.
- Do not produce a generic RCA template. Every section must be based on the evidence gathered during this investigation.

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

            response = groq.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=groq_tools,
                max_tokens=1500,

            )

            # Agent loop
            max_tool_rounds = 8
            tool_round = 0

            while response.choices[0].message.tool_calls and tool_round < max_tool_rounds:

                tool_round += 1

                print(
                    f"\n[TOOL ROUND {tool_round}/{max_tool_rounds}]"
                )

                assistant_message = {
                    "role": "assistant",
                    "content": response.choices[0].message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in response.choices[0].message.tool_calls
                    ],
                }

                messages.append(assistant_message)

                for tool_call in response.choices[0].message.tool_calls:

                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    if isinstance(tool_args, str):
                        tool_args = json.loads(tool_args)

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
                        "tool_call_id": tool_call.id,
                        "content": tool_output,
                    })

                # Ask Groq to reason over the evidence
                response = groq.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=groq_tools,
                    max_tokens=1500,

                )

            if tool_round >= max_tool_rounds:
                print(
                    "\n[WARNING] Maximum tool rounds reached. "
                    "Stopping investigation."
                )

            print("\n=== ROOT CAUSE ANALYSIS ===\n")
            print(response.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(main())
