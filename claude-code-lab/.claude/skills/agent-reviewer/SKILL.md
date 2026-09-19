---
name: agent-reviewer
description: Use when the user asks to design, review, or debug a Claude agent, tool definition, MCP server, or multi-agent system in this repo. Applies the project's agent architecture checklist.
---

# Agent reviewer

When reviewing or designing agent code in this repo:

1. Read `../common.py` first; it is the reference agent loop.
2. Check tool definitions for clear, non-overlapping descriptions and typed schemas.
3. Confirm guardrails live in tool code (see `process_refund` in lab1 as the reference pattern).
4. For multi-agent code, confirm the coordinator passes explicit context to each subagent
   and that subagents return compact, structured results.
5. Suggest the smallest change that fixes the most important issue; don't rewrite working code.
