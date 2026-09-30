import os

from dotenv import load_dotenv
import clickhouse_connect
from neo4j import GraphDatabase

load_dotenv("agent/.env")


def test_clickhouse():
    client = clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER"),
        password=os.getenv("CLICKHOUSE_PASSWORD"),
        database=os.getenv("CLICKHOUSE_DATABASE", "default"),
    )

    result = client.query("SELECT 1")
    print("ClickHouse: OK", result.result_rows)


def test_neo4j():
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(
            os.getenv("NEO4J_USER"),
            os.getenv("NEO4J_PASSWORD"),
        ),
    )

    with driver.session() as session:
        result = session.run("RETURN 1 AS value")
        print("Neo4j: OK", result.single()["value"])

    driver.close()


if __name__ == "__main__":
    test_clickhouse()
    test_neo4j()
