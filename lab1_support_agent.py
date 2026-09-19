"""
LAB 1 - Customer support agent (Domain 1: agentic loop, escalation, guardrails)

Scenario: an e-commerce support agent that can look up customers/orders,
issue refunds, and escalate to a human.

EXAM CONCEPTS
1. Agentic loop driven by stop_reason (see common.run_agent).
2. Programmatic enforcement > prompt-based guidance for hard business rules.
   The $500 refund limit is enforced INSIDE the tool, not just in the prompt.
   Prompts are guidance; code is a guarantee.
3. Escalation criteria should be explicit (policy exceptions, angry customer
   asking for a human, missing info that can't be obtained) - not "when unsure".
4. Identity verification BEFORE actions (prerequisite ordering).

Run:  python lab1_support_agent.py
Then try your own messages in the REPL at the end.
"""
from common import GREEN, RESET, run_agent
from shopkart_backend import escalate_to_human, lookup_order, process_refund, verify_customer

# ----- Tool definitions ---------------------------------------------------
# EXAM TIP (Domain 2): descriptions say WHAT, WHEN to use, and WHAT it returns.
TOOLS = [
    {
        "name": "verify_customer",
        "description": "Verify a customer's identity by matching customer ID and email. "
        "MUST succeed before any refund. Returns {verified, name} or a reason for failure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID, e.g. C100"},
                "email": {"type": "string", "description": "Email the customer provided"},
            },
            "required": ["customer_id", "email"],
        },
    },
    {
        "name": "lookup_order",
        "description": "Get an order's item, amount, status and refund state by order ID (format O-1234).",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "process_refund",
        "description": "Refund a delivered order for a VERIFIED customer. Auto-refunds are limited to "
        "$500; larger amounts are rejected and must be escalated.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason": {"type": "string", "description": "Customer's stated reason"},
            },
            "required": ["order_id", "reason"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Hand the case to a human agent. Use when: a refund exceeds policy limits, the "
        "customer explicitly asks for a human, or the issue is outside your tools. Include a summary "
        "complete enough that the human does not need to re-ask the customer anything.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "customer_id": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            },
            "required": ["summary", "customer_id", "priority"],
        },
    },
]
IMPLS = {
    "verify_customer": verify_customer,
    "lookup_order": lookup_order,
    "process_refund": process_refund,
    "escalate_to_human": escalate_to_human,
}

SYSTEM = """You are a customer support agent for ShopKart.
Workflow:
1. Verify identity (customer ID + email) before discussing or changing any order.
2. Look up the order before acting on it.
3. Refund only when policy allows. If a tool rejects an action, explain briefly and
   escalate when the rejection says to.
4. Escalate if the customer asks for a human. Do not escalate just because a task is
   slightly complex - resolve what you can first.
Be concise and friendly. Never invent order details."""

SCENARIOS = [
    # Happy path: verify -> lookup -> refund
    "Hi, I'm customer C100, email priya@example.com. My headphones (order O-5001) broke, I want a refund.",
    # Hits the programmatic $500 limit -> should escalate with a full summary
    "Customer C100 here, priya@example.com. Refund my laptop order O-5002 please, the screen is dead.",
    # Wrong email -> must NOT refund
    "I'm C200, rahul@wrong.com. Refund O-6001.",
]

if __name__ == "__main__":
    for msg in SCENARIOS:
        print("\n" + "=" * 80 + f"\nUSER: {msg}")
        answer, _ = run_agent(SYSTEM, [{"role": "user", "content": msg}], TOOLS, IMPLS, label="support")
        print(f"{GREEN}AGENT: {answer}{RESET}")

    print("\nInteractive mode (Ctrl+C to quit). The conversation keeps its history.")
    history = []
    while True:
        history.append({"role": "user", "content": input("\nYOU: ")})
        answer, history = run_agent(SYSTEM, history, TOOLS, IMPLS, label="support")
        print(f"{GREEN}AGENT: {answer}{RESET}")
