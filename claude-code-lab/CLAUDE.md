# Project memory for cca-agent-lab (loaded automatically by Claude Code)

## Project
Practice agents for the Claude Certified Architect exam, written in Python with the Anthropic SDK.
Shared agent loop lives in @../common.py — reuse it; don't write new loops.

## Conventions
- Every tool definition needs: purpose, when to use, input format, what it returns.
- Business rules (limits, permissions) are enforced in tool code, never only in prompts.
- Tool errors are returned to the model as `is_error: true` with a category and `retryable` flag.
- Model name comes from the CLAUDE_MODEL env var via common.MODEL; never hard-code it.

## Commands
- Run a lab: `python ../lab1_support_agent.py`
- Syntax check everything: `python -m py_compile ../*.py`
