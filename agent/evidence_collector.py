import json
from datetime import datetime

from cli_agent_backup import query_clickhouse, get_dependencies


# ---------------------------------------------------------
# Evidence queries
# ---------------------------------------------------------

def get_payment_errors(limit=10):
    sql = f"""
    SELECT
        Timestamp,
        SeverityText,
        Body
    FROM default.otel_logs
    WHERE
        SeverityText = 'error'
        AND (
            Body ILIKE '%Visa cache%'
            OR Body ILIKE '%payment%'
            OR Body ILIKE '%charge%'
        )
    ORDER BY Timestamp DESC
    LIMIT {limit}
    """

    return query_clickhouse(sql)


def get_failed_payment_traces(limit=10):
    sql = f"""
    SELECT
        Timestamp,
        SpanName,
        StatusCode,
        StatusMessage
    FROM default.otel_traces
    WHERE
        StatusCode = 'Error'
        AND (
            SpanName ILIKE '%Payment%'
            OR SpanName ILIKE '%Charge%'
            OR StatusMessage ILIKE '%Visa cache%'
        )
    ORDER BY Timestamp DESC
    LIMIT {limit}
    """

    return query_clickhouse(sql)


def get_visa_cache_metrics(limit=10):
    sql = f"""
    SELECT
        TimeUnix,
        Value
    FROM default.otel_metrics_gauge
    WHERE
        MetricName = 'visa_validation_cache.size'
    ORDER BY TimeUnix DESC
    LIMIT {limit}
    """

    return query_clickhouse(sql)


def get_payment_dependencies():
    return get_dependencies("payment")


# ---------------------------------------------------------
# Collect all RCA evidence
# ---------------------------------------------------------

def collect_payment_rca_evidence():

    evidence = {
        "incident": "Payment service failure",
        "collected_at": datetime.now().isoformat(),
        "logs": get_payment_errors(),
        "traces": get_failed_payment_traces(),
        "metrics": get_visa_cache_metrics(),
        "dependencies": get_payment_dependencies(),
    }

    return evidence


# ---------------------------------------------------------
# Pretty output
# ---------------------------------------------------------

def print_evidence(evidence):

    print("\n")
    print("=" * 70)
    print("AI ROOT CAUSE AGENT - EVIDENCE COLLECTION")
    print("=" * 70)

    print("\n[1] ERROR LOGS")
    print("-" * 70)

    for row in evidence["logs"]:
        print(
            f"{row.get('Timestamp')} | "
            f"{row.get('SeverityText')} | "
            f"{row.get('Body')}"
        )

    print("\n[2] FAILED TRACES")
    print("-" * 70)

    for row in evidence["traces"]:
        print(
            f"{row.get('Timestamp')} | "
            f"{row.get('SpanName')} | "
            f"{row.get('StatusCode')} | "
            f"{row.get('StatusMessage')}"
        )

    print("\n[3] VISA CACHE METRICS")
    print("-" * 70)

    for row in evidence["metrics"]:
        print(
            f"{row.get('TimeUnix')} | "
            f"value={row.get('Value')}"
        )

    print("\n[4] SERVICE DEPENDENCIES")
    print("-" * 70)

    for row in evidence["dependencies"]:
        print(
            f"{row.get('service')} "
            f"--{row.get('relationship')}--> "
            f"{row.get('dependency')}"
        )

    print("\n")
    print("=" * 70)
    print("EVIDENCE COLLECTION COMPLETE")
    print("=" * 70)


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

if __name__ == "__main__":

    try:
        evidence = collect_payment_rca_evidence()

        print_evidence(evidence)

        # Save evidence for the future LLM layer
        with open(
            "agent/evidence.json",
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                evidence,
                file,
                indent=2,
                default=str,
            )

        print("\nEvidence saved to:")
        print("agent/evidence.json")

    except Exception as error:

        print("\nERROR collecting evidence:")
        print(error)
