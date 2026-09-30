import os
from pathlib import Path
from dotenv import load_dotenv
import clickhouse_connect
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent / ".env")

clickhouse = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
    username=os.getenv("CLICKHOUSE_USER", "api"),
    password=os.getenv("CLICKHOUSE_PASSWORD", "api"),
    database=os.getenv("CLICKHOUSE_DATABASE", "default"),
)
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "rootcause")),
)

def query_clickhouse(sql: str):
    statement = sql.strip().rstrip(";").strip()
    first = statement.split(None, 1)[0].lower() if statement else ""
    if first not in {"select", "show", "describe", "desc", "with", "explain"}:
        raise ValueError("Only read-only SQL statements are allowed.")
    if ";" in statement:
        raise ValueError("Only one SQL statement is allowed.")
    result = clickhouse.query(statement)
    return [dict(zip(result.column_names, row)) for row in result.result_rows]

def get_dependencies(service: str):
    with neo4j_driver.session() as session:
        result = session.run("""
            MATCH (s:Service {name: $service})-[r]->(d:Service)
            RETURN s.name AS service, type(r) AS relationship,
                   d.name AS connected_service, 'outgoing' AS direction
            UNION ALL
            MATCH (s:Service)-[r]->(d:Service {name: $service})
            RETURN d.name AS service, type(r) AS relationship,
                   s.name AS connected_service, 'incoming' AS direction
            ORDER BY direction, connected_service
        """, service=service)
        return [dict(row) for row in result]


def investigate_payment_incident():
    """
    Collect compact evidence for payment failure investigation.
    Limits returned samples to reduce Groq token usage.
    """

    evidence = {}

    queries = {
        "logs": """
            SELECT
                Timestamp,
                SeverityText,
                ServiceName,
                Body
            FROM otel_logs
            WHERE
                lower(Body) LIKE '%visa%'
                OR lower(Body) LIKE '%payment%'
                OR lower(Body) LIKE '%charge%'
                OR lower(Body) LIKE '%checkout%'
            ORDER BY Timestamp DESC
            LIMIT 3
        """,

        "traces": """
            SELECT
                Timestamp,
                ServiceName,
                SpanName,
                StatusCode,
                StatusMessage,
                TraceId
            FROM otel_traces
            WHERE
                lower(SpanName) LIKE '%payment%'
                OR lower(SpanName) LIKE '%checkout%'
                OR lower(StatusMessage) LIKE '%visa%'
                OR lower(StatusMessage) LIKE '%cache%'
            ORDER BY Timestamp DESC
            LIMIT 3
        """,

        "metrics": """
            SELECT
                TimeUnix,
                ServiceName,
                MetricName,
                Value
            FROM otel_metrics_gauge
            WHERE MetricName = 'visa_validation_cache.size'
            ORDER BY TimeUnix DESC
            LIMIT 3
        """
    }

    for section, sql in queries.items():
        try:
            result = query_clickhouse(sql)

            if isinstance(result, dict):
                evidence[section] = result
            else:
                evidence[section] = {
                    "samples": result,
                    "sample_limit": 3
                }

        except Exception as e:
            evidence[section] = {
                "error": str(e)
            }

    try:
        evidence["payment_dependencies"] = get_dependencies("payment")
        evidence["checkout_dependencies"] = get_dependencies("checkout")
    except Exception as e:
        evidence["dependency_error"] = str(e)

    return evidence
