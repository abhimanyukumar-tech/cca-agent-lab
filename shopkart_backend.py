"""
Fake ShopKart backend shared by Lab 1 (agent) and Lab 6 (MCP server).
Business rules are enforced HERE, in code - not in the prompt.
"""
GREEN, RESET = "\033[32m", "\033[0m"

# ----- Fake backend -------------------------------------------------------
CUSTOMERS = {
    "C100": {"name": "Priya Sharma", "email": "priya@example.com", "verified": False},
    "C200": {"name": "Rahul Verma", "email": "rahul@example.com", "verified": False},
}
ORDERS = {
    "O-5001": {"customer_id": "C100", "item": "Headphones", "amount": 120.0, "status": "delivered", "refunded": False},
    "O-5002": {"customer_id": "C100", "item": "Laptop", "amount": 1450.0, "status": "delivered", "refunded": False},
    "O-6001": {"customer_id": "C200", "item": "Keyboard", "amount": 60.0, "status": "in_transit", "refunded": False},
}
REFUND_LIMIT = 500.0


def verify_customer(customer_id: str, email: str):
    c = CUSTOMERS.get(customer_id)
    if not c:
        raise ValueError(f"No customer {customer_id}")
    if c["email"].lower() != email.lower():
        return {"verified": False, "reason": "email does not match our records"}
    c["verified"] = True
    return {"verified": True, "name": c["name"]}


def lookup_order(order_id: str):
    o = ORDERS.get(order_id)
    if not o:
        raise ValueError(f"Order {order_id} not found. Ask the customer to re-check the ID.")
    return {"order_id": order_id, **o}


def process_refund(order_id: str, reason: str):
    o = ORDERS.get(order_id)
    if not o:
        raise ValueError(f"Order {order_id} not found")
    # ---- PROGRAMMATIC GUARDRAILS (the exam loves this distinction) ----
    if not CUSTOMERS[o["customer_id"]]["verified"]:
        raise PermissionError("Customer not verified. Call verify_customer first.")
    if o["refunded"]:
        raise ValueError("Order already refunded.")
    if o["status"] != "delivered":
        raise ValueError(f"Order status is '{o['status']}'; only delivered orders can be refunded.")
    if o["amount"] > REFUND_LIMIT:
        raise PermissionError(
            f"Amount {o['amount']} exceeds the {REFUND_LIMIT} auto-refund limit. Escalate to a human."
        )
    o["refunded"] = True
    return {"refunded": True, "order_id": order_id, "amount": o["amount"]}


def escalate_to_human(summary: str, customer_id: str, priority: str):
    print(f"{GREEN}*** ESCALATED [{priority}] {customer_id}: {summary}{RESET}")
    return {"ticket": "HUM-" + customer_id, "status": "queued", "eta": "4 business hours"}
