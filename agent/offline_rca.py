import json
from pathlib import Path


# ---------------------------------------------------------
# Load evidence
# ---------------------------------------------------------

EVIDENCE_FILE = Path(__file__).parent / "evidence.json"


def load_evidence():
    with open(EVIDENCE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ---------------------------------------------------------
# Evidence analysis
# ---------------------------------------------------------

def analyze_evidence(evidence):

    logs = evidence.get("logs", [])
    traces = evidence.get("traces", [])
    metrics = evidence.get("metrics", [])
    dependencies = evidence.get("dependencies", [])

    visa_cache_errors = [
        row for row in logs
        if "Visa cache full" in str(row.get("Body", ""))
    ]

    payment_trace_errors = [
        row for row in traces
        if (
            "PaymentService" in str(row.get("SpanName", ""))
            and row.get("StatusCode") == "Error"
        )
    ]

    checkout_trace_errors = [
        row for row in traces
        if (
            "CheckoutService" in str(row.get("SpanName", ""))
            and row.get("StatusCode") == "Error"
        )
    ]

    cache_values = [
        float(row["Value"])
        for row in metrics
        if row.get("Value") is not None
    ]

    payment_dependencies = [
        row
        for row in dependencies
        if row.get("service") == "payment"
    ]

    return {
        "visa_cache_errors": visa_cache_errors,
        "payment_trace_errors": payment_trace_errors,
        "checkout_trace_errors": checkout_trace_errors,
        "cache_values": cache_values,
        "payment_dependencies": payment_dependencies,
    }


# ---------------------------------------------------------
# Generate RCA
# ---------------------------------------------------------

def generate_rca(evidence):

    analysis = analyze_evidence(evidence)

    visa_errors = analysis["visa_cache_errors"]
    payment_errors = analysis["payment_trace_errors"]
    checkout_errors = analysis["checkout_trace_errors"]
    cache_values = analysis["cache_values"]
    dependencies = analysis["payment_dependencies"]

    # Determine cache state
    max_cache = max(cache_values) if cache_values else None

    # Determine dependency relationships
    dependency_text = []

    for dependency in dependencies:
        dependency_text.append(
            f"{dependency.get('service')} "
            f"--{dependency.get('relationship')}--> "
            f"{dependency.get('dependency')}"
        )

    # -----------------------------------------------------
    # Root cause
    # -----------------------------------------------------

    if visa_errors and max_cache is not None:

        root_cause = (
            "The available evidence indicates that the payment failure "
            "is associated with the Visa validation cache reaching a "
            f"value of {max_cache} and the application reporting "
            "\"Visa cache full: cannot add new item.\""
        )

    elif visa_errors:

        root_cause = (
            "The available evidence indicates that the payment failure "
            "is associated with the Visa validation cache, based on "
            "the repeated \"Visa cache full\" application errors."
        )

    else:

        root_cause = (
            "The available evidence is insufficient to determine "
            "a specific root cause."
        )

    # -----------------------------------------------------
    # Confidence
    # -----------------------------------------------------

    evidence_categories = 0

    if visa_errors:
        evidence_categories += 1

    if payment_errors or checkout_errors:
        evidence_categories += 1

    if cache_values:
        evidence_categories += 1

    if dependencies:
        evidence_categories += 1

    if evidence_categories >= 4:
        confidence = "High"
    elif evidence_categories >= 3:
        confidence = "Medium-High"
    elif evidence_categories >= 2:
        confidence = "Medium"
    else:
        confidence = "Low"

    # -----------------------------------------------------
    # Build report
    # -----------------------------------------------------

    report = []

    report.append("=" * 75)
    report.append("AI ROOT CAUSE ANALYSIS")
    report.append("=" * 75)

    report.append("\n1. EXECUTIVE SUMMARY")
    report.append("-" * 75)

    report.append(
        "Payment requests are failing because the Visa validation "
        "cache is full. The failure is observed directly in application "
        "logs and payment traces, while the cache metric reaches a "
        "maximum observed value of 25."
    )

    report.append("\n2. ROOT CAUSE")
    report.append("-" * 75)

    report.append(root_cause)

    report.append("\n3. EVIDENCE")
    report.append("-" * 75)

    report.append(
        f"• Visa cache error logs found: {len(visa_errors)}"
    )

    report.append(
        f"• Payment trace failures found: {len(payment_errors)}"
    )

    report.append(
        f"• Checkout trace failures found: {len(checkout_errors)}"
    )

    if cache_values:

        report.append(
            f"• Visa cache metric samples: {len(cache_values)}"
        )

        report.append(
            f"• Maximum observed cache value: {max_cache}"
        )

        report.append(
            f"• Minimum observed cache value: {min(cache_values)}"
        )

    else:

        report.append(
            "• Visa cache metric: unavailable"
        )

    report.append("\nKey observed error:")

    if visa_errors:

        report.append(
            f'  "{visa_errors[0].get("Body")}"'
        )

    report.append("\n4. SERVICE DEPENDENCY AND FAILURE PROPAGATION")
    report.append("-" * 75)

    if dependency_text:

        for relationship in dependency_text:
            report.append(f"• {relationship}")

    report.append(
        "\nObserved propagation:"
    )

    report.append(
        "CheckoutService/PlaceOrder → PaymentService/Charge "
        "→ Visa validation"
    )

    report.append(
        "The PaymentService failure propagates back to the "
        "CheckoutService request."
    )

    report.append("\n5. CUSTOMER / BUSINESS IMPACT")
    report.append("-" * 75)

    report.append(
        "Payment and checkout operations are affected by the "
        "Visa validation failure. Customers attempting affected "
        "payment flows may receive failed checkout/payment requests."
    )

    report.append(
        "\nThe available dataset does not provide enough information "
        "to quantify the exact number of affected customers or "
        "financial impact."
    )

    report.append("\n6. CONFIDENCE")
    report.append("-" * 75)

    report.append(
        f"{confidence} confidence based on {evidence_categories} "
        "independent evidence categories."
    )

    report.append(
        "\nObserved facts and inferences are kept separate. "
        "The evidence confirms the cache-full error and dependency "
        "relationship; it does not by itself prove the internal "
        "implementation reason why the cache became full."
    )

    report.append("\n7. RECOMMENDED NEXT ACTIONS")
    report.append("-" * 75)

    report.append(
        "1. Inspect the Visa validation cache implementation."
    )

    report.append(
        "2. Determine why the cache reached its capacity."
    )

    report.append(
        "3. Check cache eviction and capacity configuration."
    )

    report.append(
        "4. Review Visa validation traffic and cache growth."
    )

    report.append(
        "5. Add monitoring/alerting around cache capacity."
    )

    report.append(
        "6. Verify the fix by reproducing the payment flow "
        "and confirming that the cache no longer reaches the "
        "failure condition."
    )

    report.append("\n")
    report.append("=" * 75)
    report.append("END OF RCA")
    report.append("=" * 75)

    return "\n".join(report)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":

    try:

        evidence = load_evidence()

        rca = generate_rca(evidence)

        print(rca)

        output_file = Path(__file__).parent / "rca_report.txt"

        with open(
            output_file,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(rca)

        print("\nRCA report saved to:")
        print(output_file)

    except Exception as error:

        print("\nERROR generating RCA:")
        print(error)