import clickhouse_connect

client = clickhouse_connect.get_client(
    host="localhost",
    port=8123,
    username="api",
    password="api",
)


def get_errors(limit=20):
    result = client.query(f"""
        SELECT
            Timestamp,
            ServiceName,
            SeverityText,
            Body
        FROM default.otel_logs
        WHERE lower(SeverityText) = 'error'
        ORDER BY Timestamp DESC
        LIMIT {limit}
    """)

    return result.result_rows


def get_failed_traces(limit=20):
    result = client.query(f"""
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
        LIMIT {limit}
    """)

    return result.result_rows

def get_metrics(metric_name="visa_validation_cache.size", limit=20):
    result = client.query(f"""
        SELECT
            TimeUnix,
            ServiceName,
            MetricName,
            Value,
            Attributes
        FROM default.otel_metrics_gauge
        WHERE MetricName = '{metric_name}'
        ORDER BY TimeUnix DESC
        LIMIT {limit}
    """)

    return result.result_rows



if __name__ == "__main__":
    print("Searching for errors...")

    errors = get_errors()

    for error in errors:
        print(error)

    print("\nSearching for failed traces...")

    traces = get_failed_traces()

    for trace in traces:
        print(trace)

    print("\nSearching for Visa validation cache metrics...")

    metrics = get_metrics()

    for metric in metrics:
        print(metric)
