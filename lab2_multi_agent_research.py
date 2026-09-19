"""
LAB 2 - Coordinator + subagents (Domain 1: multi-agent orchestration)

Scenario: a research coordinator answers a question using an internal document
corpus. It (1) decomposes the question, (2) runs specialist subagents in
parallel, (3) synthesises a cited answer.

EXAM CONCEPTS
1. Hub-and-spoke: ONE coordinator owns the plan and final answer; subagents
   never talk to each other - everything flows through the hub.
2. Subagents do NOT inherit the coordinator's context. Whatever a subagent
   needs (its task, constraints, output format) must be passed EXPLICITLY.
3. Context isolation is the benefit: each subagent gets a small, focused
   context, and returns a compact result instead of its full transcript.
4. Structured hand-offs: subagents return JSON-shaped findings with sources,
   so the coordinator can synthesise and cite reliably.
5. Parallelise independent subtasks; run dependent ones sequentially.
6. Common failure: decomposition too narrow -> coverage gaps. The coordinator
   checks coverage before synthesising.

Run:  python lab2_multi_agent_research.py
"""
import json
from concurrent.futures import ThreadPoolExecutor

from common import GREEN, MODEL, RESET, client, run_agent, text_of

# ----- Tiny internal corpus the subagents can search ------------------------
DOCS = {
    "D1": "Q2 incident report: payment-service outage lasted 47 minutes on 12 May. Root cause was "
    "HikariCP connection pool exhaustion after a config change reduced max pool size from 50 to 10.",
    "D2": "Q2 incident report: search-service latency spike on 3 June caused by an unindexed query "
    "introduced in release 4.2. Fixed by adding a composite index. Customer impact: low.",
    "D3": "Engineering survey 2026: 62% of engineers use AI coding tools daily. Top concern is review "
    "burden for AI-generated code. Teams with mandatory AI-code review rules reported fewer defects.",
    "D4": "Cost report Q2: AWS spend rose 18% QoQ, mainly Aurora Serverless ACU scaling during load "
    "tests and idle ECS tasks in non-prod environments.",
    "D5": "Postmortem action items: add pool-size alerts, require config-change review for DB settings, "
    "schedule non-prod ECS scale-down outside business hours.",
}


def search_docs(query: str):
    """Naive keyword search - good enough to practise tool use."""
    words = {w.lower().strip(",.?") for w in query.split() if len(w) > 3}
    hits = [
        {"doc_id": d, "text": t}
        for d, t in DOCS.items()
        if words & {w.lower().strip(",.:") for w in t.split()}
    ]
    return hits or [{"note": "no matches - try different keywords"}]


SEARCH_TOOL = [{
    "name": "search_docs",
    "description": "Keyword search over internal engineering reports. Returns matching docs with doc_id. "
    "Use short keyword queries (e.g. 'outage root cause'); run several searches if the first misses.",
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
}]

# ----- Step 1: coordinator plans (structured output via a forced tool) -------
PLAN_TOOL = {
    "name": "submit_plan",
    "description": "Submit the research plan as independent subtasks.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subtasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "objective": {"type": "string", "description": "Self-contained goal for a subagent"},
                        "suggested_keywords": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "objective", "suggested_keywords"],
                },
                "minItems": 2,
                "maxItems": 4,
            }
        },
        "required": ["subtasks"],
    },
}


def plan(question: str):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system="You are a research coordinator. Break the question into 2-4 INDEPENDENT subtasks that "
        "together cover every part of it. Each objective must be understandable on its own, because the "
        "subagent will NOT see the original question.",
        tools=[PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_plan"},  # force structured output
        messages=[{"role": "user", "content": question}],
    )
    return next(b.input for b in resp.content if b.type == "tool_use")["subtasks"]


# ----- Step 2: subagents (fresh, isolated context each) ----------------------
SUBAGENT_SYSTEM = """You are a research subagent. Use search_docs to complete ONE objective.
Return ONLY JSON: {"findings": [{"claim": str, "doc_id": str}], "gaps": [str]}.
Every claim must cite the doc_id it came from. List anything you could not find under gaps."""


def run_subagent(task):
    # NOTE: the subagent gets ONLY its objective + hints - not the coordinator's history.
    prompt = f"Objective: {task['objective']}\nSuggested keywords: {', '.join(task['suggested_keywords'])}"
    text, _ = run_agent(SUBAGENT_SYSTEM, [{"role": "user", "content": prompt}], SEARCH_TOOL,
                        {"search_docs": search_docs}, max_steps=6, label=f"sub-{task['id']}")
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        return {"task": task["objective"], **json.loads(text[start:end])}
    except ValueError:
        return {"task": task["objective"], "findings": [], "gaps": ["subagent returned unparseable output"]}


# ----- Step 3: coordinator synthesises --------------------------------------
def synthesise(question, results):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system="You are the research coordinator. Write the final answer using ONLY the subagent findings. "
        "Cite doc_ids in [brackets]. If findings conflict or gaps remain, say so explicitly.",
        messages=[{"role": "user", "content": f"Question: {question}\n\nSubagent results:\n"
                   + json.dumps(results, indent=2)}],
    )
    return text_of(resp)


if __name__ == "__main__":
    question = ("What caused our Q2 production incidents, what did they cost us in cloud spend, "
                "and what actions were agreed to prevent a repeat?")
    print(f"QUESTION: {question}\n")

    subtasks = plan(question)
    print("PLAN:\n" + json.dumps(subtasks, indent=2) + "\n")

    with ThreadPoolExecutor(max_workers=len(subtasks)) as pool:  # independent -> parallel
        results = list(pool.map(run_subagent, subtasks))

    print(f"\n{GREEN}FINAL ANSWER:\n{synthesise(question, results)}{RESET}")
