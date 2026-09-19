"""
LAB 6 - Build an MCP server (Domain 2: MCP integration)

Exposes the ShopKart backend (shared with Lab 1) as an MCP server so ANY MCP client
(Claude Code, Claude Desktop, other agents) can use the same tools.

EXAM CONCEPTS
1. MCP primitives: TOOLS (model-invoked actions), RESOURCES (read-only data the
   client/app can attach as context), PROMPTS (reusable templates).
2. Transport: stdio for local servers launched by the client; HTTP for remote/shared.
3. Scope in Claude Code: project-level config (.mcp.json, committed, shared with the
   team) vs user-level config (personal, across projects). Keep secrets in env
   variables, never hard-coded in a committed .mcp.json.
4. The same tool-design rules apply: clear descriptions, typed inputs, clear errors.

Setup:
    pip install mcp
Try it in Claude Code (from this folder):
    claude mcp add shopkart-support -- python lab6_mcp_server.py
    claude            # then ask: "look up order O-5001 using the shopkart tools"
Or use claude-code-lab/.mcp.json for the project-scoped version.
"""
from mcp.server.fastmcp import FastMCP

from shopkart_backend import CUSTOMERS, ORDERS, lookup_order, verify_customer  # no API key needed

mcp = FastMCP("shopkart-support")


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Get an order's item, amount, status and refund state by order ID (format O-1234)."""
    return lookup_order(order_id)


@mcp.tool()
def verify(customer_id: str, email: str) -> dict:
    """Verify a customer's identity by customer ID + email. Required before any account action."""
    return verify_customer(customer_id, email)


@mcp.resource("shopkart://refund-policy")
def refund_policy() -> str:
    """Read-only refund policy text (a RESOURCE, not a tool)."""
    return "Delivered orders may be auto-refunded up to $500 for verified customers. Above that: escalate."


@mcp.resource("shopkart://customers/{customer_id}/orders")
def customer_orders(customer_id: str) -> str:
    """All orders for a customer (templated resource)."""
    rows = [f"{oid}: {o['item']} ${o['amount']} ({o['status']})"
            for oid, o in ORDERS.items() if o["customer_id"] == customer_id]
    if customer_id not in CUSTOMERS:
        return "Unknown customer"
    return "\n".join(rows) or f"No orders for {customer_id}"


@mcp.prompt()
def refund_triage(order_id: str) -> str:
    """Reusable PROMPT template for triaging a refund request."""
    return (f"Triage a refund for order {order_id}: verify the customer, read shopkart://refund-policy, "
            f"look up the order, then recommend refund / escalate / deny with one-line reasoning.")


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
