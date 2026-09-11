import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():

    server_params = StdioServerParameters(
        command="mcp-clickhouse",
        args=[],
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            print("\n=== RCA INVESTIGATION ===\n")

            # 1. Errors
            print("1. PAYMENT ERRORS\n")

            errors_query = """
            SELECT
                Timestamp,
                ServiceName,
                Body
            FROM default.otel_logs
            WHERE lower(SeverityText) = 'error'
            ORDER BY Timestamp DESC
            LIMIT 10
            """

            errors = await session.call_tool(
                "run_query",
                {"query": errors_query}
            )

            print(errors)

            # 2. Failed traces
            print("\n2. FAILED TRACES\n")

            traces_query = """
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

            traces = await session.call_tool(
                "run_query",
                {"query": traces_query}
            )

            print(traces)

            # 3. Visa validation cache
            print("\n3. VISA VALIDATION CACHE\n")

            metrics_query = """
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

            metrics = await session.call_tool(
                "run_query",
                {"query": metrics_query}
            )

            print(metrics)


if __name__ == "__main__":
    asyncio.run(main())
