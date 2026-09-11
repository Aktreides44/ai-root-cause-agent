from neo4j import GraphDatabase


driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "rootcause"),
)


def get_dependencies(service):
    query = """
    MATCH (s:Service {name: $service})-[r:CALLS]->(dependency:Service)
    RETURN s.name AS service,
           type(r) AS relationship,
           dependency.name AS dependency
    """

    with driver.session() as session:
        result = session.run(query, service=service)
        return [record.data() for record in result]


if __name__ == "__main__":
    print("Checking checkout dependencies...")

    dependencies = get_dependencies("checkout")

    for dependency in dependencies:
        print(dependency)

    driver.close()
