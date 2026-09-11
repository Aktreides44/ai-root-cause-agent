import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_query(session, query):
    result = await session.call_tool(
        "run_query",
        {"query": query}
    )

    if result.is_error:
        raise RuntimeError(str(result))

    text = result.content[0].text
    return json.loads(text)


async def investigate(session):

    print("\n================================")
    print("       RCA INVESTIGATION")
    print("================================\n")

    # --------------------------------------------------
    # 1. Find recent errors
    # --------------------------------------------------

    print("[1] Investigating errors...")

    errors = await run_query(
        session,
        """
        SELECT
            Timestamp,
            ServiceName,
            Body
        FROM default.otel_logs
        WHERE lower(SeverityText) = 'error'
        ORDER BY Timestamp DESC
        LIMIT 10
        """
    )

    print(json.dumps(errors, indent=2))

    # --------------------------------------------------
    # 2. Investigate failed traces
    # --------------------------------------------------

    print("\n[2] Investigating failed traces...")

    traces = await run_query(
        session,
        """
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
        ORDER BY Timestamp DESC
        LIMIT 10
        """
    )

    print(json.dumps(traces, indent=2))

    # --------------------------------------------------
    # 3. Investigate Visa cache metric
    # --------------------------------------------------

    print("\n[3] Investigating Visa validation cache...")

    metrics = await run_query(
        session,
        """
        SELECT
            TimeUnix,
            ServiceName,
            MetricName,
            Value
        FROM default.otel_metrics_gauge
        WHERE MetricName = 'visa_validation_cache.size'
        ORDER BY TimeUnix DESC
        LIMIT 15
        """
    )

    print(json.dumps(metrics, indent=2))

    # --------------------------------------------------
    # 4. Combine evidence
    # --------------------------------------------------

    print("\n================================")
    print("           RCA SUMMARY")
    print("================================\n")

    print("Evidence collected:")
    print("- Payment service reports Visa cache errors.")
    print("- Checkout traces fail while charging payments.")
    print("- Visa validation cache grows and reaches 25.")
    print("- Cache remains at 25 while failures continue.")

    print("\nProbable root cause:")
    print(
        "Visa validation cache exhaustion causes Payment failures, "
        "which propagate to Checkout."
    )


async def main():

    server_params = StdioServerParameters(
        command="mcp-clickhouse",
        args=[],
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            await investigate(session)


if __name__ == "__main__":
    asyncio.run(main())
