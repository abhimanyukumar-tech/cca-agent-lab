"""
LAB 3 - Tool design experiments (Domain 2: tool design)

Same backend, two tool sets: VAGUE vs WELL-DESIGNED. Run identical user
requests against both and watch which tool Claude picks.

EXAM CONCEPTS
1. Tool descriptions are the main lever for tool selection. Overlapping,
   vague tools ("search" vs "get") cause mis-selection. Fix the DESCRIPTION
   (purpose, when to use, when NOT to use, input format, output) first.
2. Too many tools degrade selection. Give each agent only the tools its role needs.
3. Structured errors: return is_error=True with a category and whether it is
   retryable, so the model can decide to retry, change input, or give up.
4. tool_choice:
     {"type": "auto"}            model decides (default)
     {"type": "any"}             must call SOME tool
     {"type": "tool", "name": X} must call tool X (forced / structured output)
     {"type": "none"}            no tools this turn

Run:  python lab3_tool_design.py
"""
import json

from common import MODEL, client

EMPLOYEES = {"E1": {"name": "Anita Rao", "team": "Payments", "manager": "E9"},
             "E9": {"name": "Vikram Nair", "team": "Payments", "manager": None}}
TICKETS = [{"id": "T-1", "assignee": "E1", "title": "Pool exhaustion alert", "state": "open"}]

VAGUE_TOOLS = [
    {"name": "search", "description": "Searches for things.",
     "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}},
    {"name": "get", "description": "Gets data.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]

GOOD_TOOLS = [
    {"name": "find_employee",
     "description": "Find employees by (partial) name. Use when you only have a person's name and need "
     "their employee ID. Returns a list of {employee_id, name, team}. Do NOT use for tickets.",
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "Full or partial name, e.g. 'Anita'"}}, "required": ["name"]}},
    {"name": "get_employee",
     "description": "Get one employee's details (team, manager ID) by employee ID (format E<number>). "
     "Use after find_employee, or when the ID is already known.",
     "input_schema": {"type": "object", "properties": {
         "employee_id": {"type": "string", "pattern": "^E\\d+$"}}, "required": ["employee_id"]}},
    {"name": "list_tickets",
     "description": "List support tickets assigned to an employee ID. Returns {id, title, state}. "
     "Use for questions about someone's work items, not about the person themselves.",
     "input_schema": {"type": "object", "properties": {
         "assignee_id": {"type": "string"},
         "state": {"type": "string", "enum": ["open", "closed", "any"], "default": "any"}},
         "required": ["assignee_id"]}},
]

REQUESTS = [
    "Who is Anita's manager?",
    "What open tickets does Anita have?",
]


def first_tool_choice(tools, request, tool_choice=None):
    """Return the tool calls from Claude's first turn only - enough to judge tool selection."""
    kwargs = {"tool_choice": tool_choice} if tool_choice else {}
    resp = client.messages.create(model=MODEL, max_tokens=512, tools=tools,
                                  messages=[{"role": "user", "content": request}], **kwargs)
    return [(b.name, b.input) for b in resp.content if b.type == "tool_use"] or ["(no tool call)"]


def structured_error_demo():
    """Show how Claude reacts to a well-formed, categorised tool error."""
    tools = GOOD_TOOLS
    messages = [{"role": "user", "content": "Get details for employee E77."}]
    resp = client.messages.create(model=MODEL, max_tokens=512, tools=tools, messages=messages)
    call = next(b for b in resp.content if b.type == "tool_use")
    messages += [
        {"role": "assistant", "content": resp.content},
        {"role": "user", "content": [{
            "type": "tool_result", "tool_use_id": call.id, "is_error": True,
            "content": json.dumps({"error_category": "not_found", "retryable": False,
                                   "message": "No employee E77. Valid IDs look like E1, E9."}),
        }]},
    ]
    final = client.messages.create(model=MODEL, max_tokens=512, tools=tools, messages=messages)
    print("Claude after structured error:", "".join(b.text for b in final.content if b.type == "text"))


if __name__ == "__main__":
    for req in REQUESTS:
        print(f"\nREQUEST: {req}")
        print("  vague tools ->", first_tool_choice(VAGUE_TOOLS, req))
        print("  good tools  ->", first_tool_choice(GOOD_TOOLS, req))

    print("\n--- tool_choice modes on 'Hello there!' ---")
    for choice in [None, {"type": "any"}, {"type": "tool", "name": "list_tickets"}]:
        print(f"  {choice or 'auto (default)'} ->", first_tool_choice(GOOD_TOOLS, "Hello there!", choice))

    print("\n--- structured error handling ---")
    structured_error_demo()
