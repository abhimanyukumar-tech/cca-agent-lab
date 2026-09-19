---
description: Review an agent file against the exam's architecture checklist
---
Review the agent code in $ARGUMENTS against this checklist and report PASS/FAIL per item with line references:

1. Loop terminates on `stop_reason`, with a max-step cap.
2. All tool_use blocks in a turn are answered in ONE user message of tool_results.
3. Tool descriptions state purpose, when to use, inputs and outputs; no overlapping tools.
4. Hard business rules are enforced in code, not only in the prompt.
5. Errors go back to the model with `is_error` and enough detail to recover.
6. Subagents (if any) receive all needed context explicitly.
7. Structured output uses a forced tool / schema plus semantic validation.

End with the single highest-impact fix.
