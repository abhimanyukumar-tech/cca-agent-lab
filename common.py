"""
Shared helpers for all labs.

EXAM CONCEPT (Domain 1): the agentic loop is driven by `stop_reason`, not by
parsing the model's text. Keep calling the model while it asks for tools
(stop_reason == "tool_use"); stop when it ends its turn ("end_turn").
Always cap the number of steps so a confused agent can't loop forever.
"""
import json
import os
from dotenv import load_dotenv
load_dotenv()
import anthropic

# Default to Sonnet; set CLAUDE_MODEL=claude-haiku-4-5-20251001 for cheaper practice runs.
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

CYAN, YELLOW, GREEN, RED, DIM, RESET = "\033[36m", "\033[33m", "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def text_of(response) -> str:
    """Join all text blocks in a response (a response can mix text and tool_use blocks)."""
    return "".join(b.text for b in response.content if b.type == "text")


def run_agent(system, messages, tools, tool_impls, max_steps=10, verbose=True, label="agent", **create_kwargs):
    """
    Minimal but production-shaped agent loop.

    - system:      system prompt (str or list of content blocks)
    - messages:    conversation so far (mutated in place, so callers can inspect it)
    - tools:       tool definitions (name, description, input_schema)
    - tool_impls:  {tool_name: python_callable}
    Returns (final_text, messages).
    """
    for step in range(1, max_steps + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            tools=tools,
            messages=messages,
            **create_kwargs,
        )
        # The assistant turn must be appended exactly as returned (including tool_use blocks).
        messages.append({"role": "assistant", "content": response.content})

        if verbose:
            thought = text_of(response).strip()
            if thought:
                print(f"{DIM}[{label} step {step}] {thought[:300]}{RESET}")

        if response.stop_reason == "end_turn":
            return text_of(response), messages
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Response truncated (max_tokens). Raise max_tokens or reduce output.")
        if response.stop_reason != "tool_use":
            # e.g. "stop_sequence", "refusal", "pause_turn" - surface it instead of guessing.
            return text_of(response), messages

        # Execute EVERY tool_use block in this turn (Claude may request several in parallel)
        # and return ALL results in ONE user message.
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if verbose:
                print(f"{CYAN}[{label}] -> {block.name}({json.dumps(block.input)}){RESET}")
            try:
                if block.name not in tool_impls:
                    raise ValueError(f"Unknown tool '{block.name}'")
                result = tool_impls[block.name](**block.input)
                content, is_error = json.dumps(result, default=str), False
            except Exception as exc:  # errors go BACK to the model so it can recover
                content, is_error = json.dumps({"error": str(exc)}), True
            if verbose:
                colour = RED if is_error else YELLOW
                print(f"{colour}[{label}] <- {content[:300]}{RESET}")
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error}
            )
        messages.append({"role": "user", "content": tool_results})

    raise RuntimeError(f"{label}: hit max_steps={max_steps} without finishing")
