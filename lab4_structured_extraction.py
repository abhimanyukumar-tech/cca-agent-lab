"""
LAB 4 - Structured extraction + validation-retry (Domain 4: prompts & structured output)

Scenario: extract structured data from messy vendor invoices.

EXAM CONCEPTS
1. Reliable JSON: define a JSON schema as a tool and FORCE it with
   tool_choice={"type": "tool", ...}. Schema-shaped output beats
   "please reply in JSON" prompts.
2. A schema guarantees SHAPE, not CORRECTNESS. Add semantic validation in code
   (e.g. line items must sum to the total) and feed specific errors back.
3. Validation-retry loop: send the exact validation error back as an is_error
   tool_result and ask for a corrected call. Cap the retries. Retries only help
   when the information is actually in the source - if it's missing, retrying
   won't create it.
4. Nullable fields + an explicit instruction ("use null if absent") prevent
   hallucinated values for missing data.
5. Few-shot examples fix FORMAT and judgment on ambiguous cases (e.g. how to
   treat a discount line).
6. Explicit criteria ("flag only if...") reduce false positives more than
   vague instructions ("be careful").

Run:  python lab4_structured_extraction.py
"""
import json

from common import GREEN, MODEL, RED, RESET, client

INVOICE_TOOL = {
    "name": "record_invoice",
    "description": "Record the structured fields extracted from one invoice.",
    "input_schema": {
        "type": "object",
        "properties": {
            "vendor": {"type": "string"},
            "invoice_number": {"type": ["string", "null"], "description": "null if not present"},
            "invoice_date": {"type": ["string", "null"], "description": "ISO YYYY-MM-DD, null if absent"},
            "currency": {"type": "string", "enum": ["INR", "USD", "EUR"]},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "amount": {"type": "number", "description": "Negative for discounts/credits"},
                    },
                    "required": ["description", "amount"],
                },
            },
            "total": {"type": "number"},
            "needs_review": {"type": "boolean",
                             "description": "true ONLY if the stated total conflicts with the line items "
                                            "or a required value is unreadable"},
        },
        "required": ["vendor", "invoice_number", "invoice_date", "currency", "line_items", "total",
                     "needs_review"],
    },
}

SYSTEM = """You extract invoice data. Rules:
- Copy values from the document; never guess. Use null for missing optional fields.
- Dates -> ISO format. Discounts/credits are line items with NEGATIVE amounts.
- Taxes are line items.

Example
Invoice: "Acme Ltd | Inv #A-9 | 5 Mar 2026 | Widgets Rs 1,000 | Discount 10% Rs 100 | GST Rs 162 | Total Rs 1,062"
-> vendor "Acme Ltd", invoice_number "A-9", invoice_date "2026-03-05", currency "INR",
   line_items [Widgets 1000, Discount -100, GST 162], total 1062, needs_review false"""

INVOICES = [
    "CloudNine Hosting — invoice CN-2231, dated 14/08/2026. Server rental $400.00; Backup add-on $50.00; "
    "Loyalty credit ($25.00). Amount due: $425.00",
    # Missing invoice number; total deliberately inconsistent -> validation should push needs_review=true
    "Chai & Co catering, 2 Sept 2026. Team lunch Rs 3,200. Snacks Rs 800. GST Rs 720. TOTAL Rs 5,000",
]


def validate(data):
    """Semantic checks a schema can't express. Returns a list of error strings."""
    errors = []
    items_sum = round(sum(i["amount"] for i in data["line_items"]), 2)
    if abs(items_sum - data["total"]) > 0.01 and not data["needs_review"]:
        errors.append(f"line_items sum to {items_sum} but total is {data['total']}. Re-check the amounts; "
                      "if the document itself is inconsistent, keep the stated total and set needs_review=true.")
    if data["invoice_date"] and len(data["invoice_date"]) != 10:
        errors.append("invoice_date must be YYYY-MM-DD.")
    return errors


def extract(invoice_text, max_retries=2):
    messages = [{"role": "user", "content": f"Invoice:\n{invoice_text}"}]
    for attempt in range(max_retries + 1):
        resp = client.messages.create(
            model=MODEL, max_tokens=1024, system=SYSTEM, tools=[INVOICE_TOOL],
            tool_choice={"type": "tool", "name": "record_invoice"}, messages=messages,
        )
        call = next(b for b in resp.content if b.type == "tool_use")
        errors = validate(call.input)
        if not errors:
            return call.input, attempt
        print(f"{RED}  attempt {attempt}: validation failed -> {errors}{RESET}")
        # Feed the SPECIFIC error back and ask for a corrected call.
        messages += [
            {"role": "assistant", "content": resp.content},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call.id, "is_error": True,
                                          "content": "Validation failed:\n- " + "\n- ".join(errors)}]},
        ]
    raise RuntimeError("Extraction failed validation after retries - route to human review.")


if __name__ == "__main__":
    for inv in INVOICES:
        print("\nINVOICE:", inv)
        data, retries = extract(inv)
        print(f"{GREEN}  OK after {retries} retr{'y' if retries == 1 else 'ies'}:{RESET}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
