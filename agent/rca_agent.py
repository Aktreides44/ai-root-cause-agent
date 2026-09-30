import json
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from cli_agent import query_clickhouse, get_dependencies, investigate_payment_incident, neo4j_driver

load_dotenv(Path(__file__).resolve().parent / ".env")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not configured in agent/.env")
client = Groq(api_key=GROQ_API_KEY)

tools = [
 {"type":"function","function":{"name":"query_clickhouse","description":"Run one read-only SQL query against ClickHouse observability data.","parameters":{"type":"object","properties":{"sql":{"type":"string"}},"required":["sql"]}}},
 {"type":"function","function":{"name":"get_dependencies","description":"Get incoming and outgoing Neo4j service relationships.","parameters":{"type":"object","properties":{"service":{"type":"string"}},"required":["service"]}}},
 {"type":"function","function":{"name":"investigate_payment_incident","description":"Collect matching payment/checkout logs, traces, Visa cache gauge metrics, and payment/checkout Neo4j relationships for an evidence-based payment RCA.","parameters":{"type":"object","properties":{},"additionalProperties":False}}},
]

SYSTEM_PROMPT = """
You are an evidence-driven application observability assistant.
Use ClickHouse for logs, traces, metrics and schemas; use Neo4j for service topology.
Answer ordinary questions directly; do not force an RCA template for simple queries.
For payment/checkout RCA, prefer investigate_payment_incident for efficient evidence collection.
If a query fails, disclose the error; never claim it succeeded. Do not invent evidence, customer
counts, revenue, timestamps or causal mechanisms.
Separate OBSERVED FACT, INFERENCE and UNKNOWN. A cache-full error proves that the condition was
reported, but does not by itself prove why the cache reached capacity or whether eviction failed.
For RCA requests use:
1. Executive Summary
2. Root Cause (separate fact from inference)
3. Evidence
4. Service Dependency and Failure Propagation
5. Customer / Business Impact
6. Confidence and limitations
7. Recommended Next Actions
"""

def execute_tool(name, args):
    if name == "query_clickhouse": return query_clickhouse(args.get("sql", ""))
    if name == "get_dependencies": return get_dependencies(args.get("service", ""))
    if name == "investigate_payment_incident": return investigate_payment_incident()
    raise ValueError(f"Unknown tool: {name}")

def run_agent(messages):
    max_rounds = 10
    for turn in range(max_rounds):
        print(f"\n[AGENT ROUND {turn + 1}/{max_rounds}]")
        try:
            response = client.chat.completions.create(model=GROQ_MODEL, messages=messages, tools=tools, tool_choice="auto", max_tokens=2500)
        except Exception as exc:
            print(f"[LLM ERROR] {exc}")
            return
        msg = response.choices[0].message
        if not msg.tool_calls:
            print("\n" + "="*68 + "\nASSISTANT\n" + "="*68 + "\n")
            print(msg.content or "No response was returned.")
            return
        messages.append({"role":"assistant","content":msg.content or "","tool_calls":[{"id":c.id,"type":"function","function":{"name":c.function.name,"arguments":c.function.arguments}} for c in msg.tool_calls]})
        for call in msg.tool_calls:
            try: args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError: args = {}
            print(f"[TOOL] {call.function.name} | args={args}")
            try:
                result = execute_tool(call.function.name, args)
                if isinstance(result, list): print(f"[RESULT] {len(result)} records")
                elif isinstance(result, dict): print("[RESULT] evidence sections:", {k: len(v) if isinstance(v,list) else "query error" if isinstance(v,dict) and "query_error" in v else "received" for k,v in result.items()})
            except Exception as exc:
                print(f"[TOOL ERROR] {exc}")
                result = {"tool_error":str(exc)}
            messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(result,default=str)})
    print("Agent reached the round limit; ask it to summarize collected evidence.")

def main():
    print(f"AI ROOT CAUSE ANALYSIS AGENT | Groq model: {GROQ_MODEL}")
    print("Ask a question; type exit to quit.")
    messages=[{"role":"system","content":SYSTEM_PROMPT}]
    try:
        while True:
            try: question=input("> ").strip()
            except (KeyboardInterrupt,EOFError):
                print("\nExiting."); break
            if not question: continue
            if question.lower() in {"exit","quit"}: print("Goodbye."); break
            messages.append({"role":"user","content":question})
            run_agent(messages)
    finally:
        neo4j_driver.close()

if __name__ == "__main__":
    main()
