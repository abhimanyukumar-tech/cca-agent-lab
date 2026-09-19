"""
LAB 5 - Prompt caching + conversation compaction (Domain 5: context & reliability)

EXAM CONCEPTS
1. Prompt caching: mark the END of a large, STABLE prefix (tools -> system ->
   early messages) with cache_control {"type": "ephemeral"}. Later calls with
   the identical prefix read it from cache (cheaper + faster).
   - Anything that changes (timestamps, user data) must come AFTER the breakpoint,
     or it invalidates the cache.
   - Check usage.cache_creation_input_tokens vs usage.cache_read_input_tokens.
   - Prefixes below a model-specific minimum length are not cached.
2. Token budgeting: measure with messages.count_tokens BEFORE sending.
3. Compaction: when history grows past a budget, summarise OLD turns and keep
   RECENT turns verbatim. Risk: summaries drop precise facts (IDs, amounts,
   dates) -> extract those into a pinned "case facts" block that is never summarised.
4. Put critical instructions/facts where they won't get lost in the middle
   of a very long context (start of system prompt or a pinned block).

Run:  python lab5_context_management.py
"""
import json

from common import GREEN, MODEL, RESET, YELLOW, client, text_of

# ----- Part A: prompt caching ---------------------------------------------
# A long, stable "policy manual" - big enough to exceed the minimum cacheable length.
POLICY = "\n".join(
    f"Policy {i}: Refunds for category {i % 7} are allowed within {15 + i % 30} days of delivery when the "
    f"item is unused, and store credit is offered for opened items. Escalate disputes above {100 + i * 5} USD."
    for i in range(1, 160)
)

SYSTEM_BLOCKS = [
    {"type": "text", "text": "You are a support policy assistant. Answer strictly from the manual."},
    {"type": "text", "text": "POLICY MANUAL\n" + POLICY,
     "cache_control": {"type": "ephemeral"}},  # <- breakpoint: everything up to here is cached
]


def caching_demo():
    for q in ["What is the refund window for Policy 12?", "When should Policy 40 disputes escalate?"]:
        resp = client.messages.create(model=MODEL, max_tokens=200, system=SYSTEM_BLOCKS,
                                      messages=[{"role": "user", "content": q}])
        u = resp.usage
        print(f"{YELLOW}Q: {q}{RESET}\n  A: {text_of(resp)[:150]}")
        print(f"  input={u.input_tokens}  cache_write={u.cache_creation_input_tokens}  "
              f"cache_read={u.cache_read_input_tokens}")
    print("Expected: call 1 writes the cache, call 2 reads it (run twice within ~5 min to see reads).")


# ----- Part B: compaction with pinned facts -----------------------------------
TOKEN_BUDGET = 1200   # deliberately tiny so compaction triggers quickly in the demo
KEEP_RECENT = 5       # messages kept verbatim; odd so the kept slice starts on a user turn

FACTS_TOOL = {
    "name": "save_case_state",
    "description": "Save a summary of older conversation plus exact case facts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Short narrative of what happened so far"},
            "facts": {"type": "object", "description": "Exact IDs, amounts, dates, decisions - verbatim",
                      "additionalProperties": {"type": "string"}},
        },
        "required": ["summary", "facts"],
    },
}


def tokens(system, messages):
    return client.messages.count_tokens(model=MODEL, system=system, messages=messages).input_tokens


def compact(history, pinned):
    old, recent = history[:-KEEP_RECENT], history[-KEEP_RECENT:]
    resp = client.messages.create(
        model=MODEL, max_tokens=800, tools=[FACTS_TOOL],
        tool_choice={"type": "tool", "name": "save_case_state"},
        messages=[{"role": "user", "content": "Existing facts: " + json.dumps(pinned) +
                   "\n\nConversation to compact:\n" + json.dumps(old, default=str)}],
    )
    state = next(b.input for b in resp.content if b.type == "tool_use")
    pinned.update(state["facts"])  # facts are merged, never summarised away
    print(f"{GREEN}  [compacted {len(old)} messages] pinned facts now: {pinned}{RESET}")
    return [{"role": "user", "content": f"(Earlier conversation summary: {state['summary']})"},
            {"role": "assistant", "content": "Understood, continuing from that summary."}] + recent


def compaction_demo():
    pinned = {}
    history = []
    turns = [
        "Hi, my order is O-88231, a Dell monitor, paid 18,499 rupees on 2 Sept.",
        "It arrived with a dead pixel cluster in the top-left corner.",
        "I already tried the monitor's built-in pixel refresh, didn't help.",
        "I'd prefer a replacement, not a refund. My pincode is 248001.",
        "Also, can the courier pick it up on a weekend?",
        "Remind me - what was my order number and amount again?",  # tests that facts survived
    ]
    for t in turns:
        history.append({"role": "user", "content": t})
        system = "You are a support agent. Pinned case facts (authoritative): " + json.dumps(pinned)
        n = tokens(system, history)
        print(f"\nUSER: {t}\n  tokens before send: {n}")
        if n > TOKEN_BUDGET and len(history) > KEEP_RECENT:
            history = compact(history, pinned)
            system = "You are a support agent. Pinned case facts (authoritative): " + json.dumps(pinned)
        resp = client.messages.create(model=MODEL, max_tokens=300, system=system, messages=history)
        reply = text_of(resp)
        history.append({"role": "assistant", "content": reply})
        print(f"  AGENT: {reply[:200]}")


if __name__ == "__main__":
    print("=== Part A: prompt caching ===")
    caching_demo()
    print("\n=== Part B: compaction with pinned facts ===")
    compaction_demo()
