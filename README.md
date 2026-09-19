# CCA-F Agent Lab — hands-on practice for the Claude Certified Architect (Foundations) exam

Six small Python agents plus a Claude Code config lab. Each lab maps to an exam domain, and the
comment block at the top of each file lists the exam concepts it exercises.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install anthropic mcp
export ANTHROPIC_API_KEY=sk-ant-...                      # Windows: set ANTHROPIC_API_KEY=...
# Optional: cheaper practice runs
export CLAUDE_MODEL=claude-haiku-4-5-20251001            # default is claude-sonnet-5
```

## Lab → exam domain map

| Lab | File | Domain (weight) | What you practise |
|---|---|---|---|
| 1 | `lab1_support_agent.py` | D1 Agentic Architecture (27%) | Agent loop on `stop_reason`, escalation, guardrails in code |
| 2 | `lab2_multi_agent_research.py` | D1 Agentic Architecture | Hub-and-spoke coordinator, isolated subagents, parallel runs, synthesis |
| 3 | `lab3_tool_design.py` | D2 Tool Design & MCP (18%) | Vague vs clear tool descriptions, `tool_choice`, structured errors |
| 4 | `lab4_structured_extraction.py` | D4 Prompting & Structured Output (20%) | Forced-tool JSON, few-shot, validation-retry loop, nullable fields |
| 5 | `lab5_context_management.py` | D5 Context & Reliability (15%) | Prompt caching, token counting, compaction with pinned facts |
| 6 | `lab6_mcp_server.py` | D2 Tool Design & MCP | MCP tools vs resources vs prompts, stdio server |
| CC | `claude-code-lab/` | D3 Claude Code (20%) | CLAUDE.md, slash command, skill frontmatter, project `.mcp.json` |

`common.py` holds the shared agent loop, and `shopkart_backend.py` is the fake data layer used by Labs 1 and 6.

## How to practise: break things on purpose

Running a lab once teaches you little. The exam is scenario-based ("the agent does X wrong — what's
the BEST fix?"), so for each lab, make the change below, predict what will happen, run it, and
explain the result to yourself.

**Lab 1 — support agent**
- Delete the `$500` check from `process_refund` and put "never refund above $500" only in the
  system prompt instead. Try to talk the agent into refunding O-5002. *Lesson: prompts guide; code guarantees.*
- Set `max_steps=2`. *Lesson: why a step cap matters, and what failure looks like.*
- Change the escalation description to "use when unsure". Watch it over-escalate.
  *Lesson: escalation needs explicit criteria.*

**Lab 2 — multi-agent**
- Change the planner prompt to allow only 1 subtask. Check which part of the question goes unanswered.
  *Lesson: narrow decomposition causes coverage gaps.*
- In `run_subagent`, pass only `task['id']` instead of the objective. *Lesson: subagents do not
  inherit the coordinator's context.*
- Make subagents return free text instead of JSON. Compare how well the synthesis cites sources.

**Lab 3 — tool design**
- Add a third vague tool called `lookup`. See how much worse tool selection gets.
- Fix only the descriptions of the vague tools (keep their names). Does selection recover?

**Lab 4 — extraction**
- Remove the `null` instruction and the nullable types. Does it invent an invoice number for Chai & Co?
- Remove the few-shot example. Are discounts still negative?
- Make the second invoice internally consistent and confirm the retry loop does not fire.

**Lab 5 — context**
- Move the per-request user question *into* the cached system block. Watch cache reads drop to zero.
- Set `pinned = {}` and skip `pinned.update(...)`. Does the agent still remember O-88231 and 18,499?

**Lab 6 — MCP**
- Register the server in Claude Code (`claude mcp add shopkart-support -- python lab6_mcp_server.py`)
  and ask for an order. Then use the `refund_triage` prompt. Explain the difference between a tool,
  a resource, and a prompt.

**Claude Code lab** (`cd claude-code-lab && claude`)
- Run `/review-agent ../lab1_support_agent.py` (a custom slash command).
- Ask "review lab2 for architecture issues" and check whether the `agent-reviewer` skill triggers
  from its description.
- Add a `CLAUDE.md` in a subfolder and learn which memory file wins, and when each one loads.
- Try headless mode, the pattern used in CI/CD: `claude -p "review ../lab3_tool_design.py" --output-format json`
- Check exact flags and file locations against the official docs:
  https://docs.claude.com/en/docs/claude-code/overview — Domain 3 questions get specific.

## Exam traps these labs cover

- Loop on `stop_reason`, never on "does the text look finished".
- Answer every `tool_use` block in a turn, with all results together in one user message.
- For hard rules, the best answer is almost always "enforce it in code or a hook", not "add it to the prompt".
- The first fix for mis-selected tools is better descriptions. Consolidating or scoping tools comes next.
- Subagents need explicit context, and they should return compact structured results.
- A JSON schema guarantees the shape of the output, not that it is correct. Add semantic validation and targeted retries.
- A retry cannot recover information that isn't in the source. Route those cases to a human instead.
- Caching needs a stable prefix, and anything that changes goes after the breakpoint.
- Summaries lose precise facts. Pin IDs, amounts, and dates in a separate block.

## Plan until 4 October

| Days | Focus |
|---|---|
| Sep 20–22 | Labs 1–2 + all their break-it experiments (D1 is 27%) |
| Sep 23–24 | Labs 3 + 6 (Tool design & MCP) |
| Sep 25–27 | Claude Code lab + docs reading (D3 is detailed) |
| Sep 28–29 | Lab 4 (structured output) |
| Sep 30 | Lab 5 (context & caching) |
| Oct 1–2 | Official practice exam + review every wrong answer against the matching lab |
| Oct 3 | Light review of the traps list only; rest |
