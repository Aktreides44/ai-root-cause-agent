import os

from dotenv import load_dotenv
import clickhouse_connect

load_dotenv("agent/.env")

client = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST"),
    port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
    username=os.getenv("CLICKHOUSE_USER"),
    password=os.getenv("CLICKHOUSE_PASSWORD"),
    database=os.getenv("CLICKHOUSE_DATABASE", "default"),
)

queries = {
    "PAYMENT ERRORS": """
        SELECT Timestamp, Body
        FROM otel_logs
        WHERE Body LIKE '%Visa cache%'
        ORDER BY Timestamp DESC
        LIMIT 5
    """,

    "PAYMENT TRACES": """
        SELECT Timestamp, SpanName, StatusCode, StatusMessage
        FROM otel_traces
        WHERE (
            SpanName ILIKE '%payment%'
            OR SpanName ILIKE '%checkout%'
        )
        AND (
            StatusCode != '0'
            OR StatusMessage != ''
        )
        ORDER BY Timestamp DESC
        LIMIT 5
    """,

    "VISA CACHE METRIC": """
        SELECT TimeUnix, Value
        FROM otel_metrics_gauge
        WHERE MetricName ILIKE '%visa_validation_cache.size%'
        ORDER BY TimeUnix DESC
        LIMIT 10
    """,
}

for name, query in queries.items():
    print(f"\n=== {name} ===")

    try:
        result = client.query(query)

        for row in result.result_rows:
            print(row)

    except Exception as e:
        print(f"ERROR: {e}")
