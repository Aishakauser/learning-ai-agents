"""
LEVEL 1 — research_agent (rock-solid web search)

A minimal AI agent built BY HAND so you can see the think -> act -> observe loop.

Two tools:
  - web_search : Claude's OFFICIAL built-in web search (runs on Anthropic's
                 servers, returns results with citations). Reliable, no extra key.
  - calculator : a "client-side" tool that YOUR code runs.

This shows BOTH styles of tool in one place:
  * A SERVER tool (web_search) — Anthropic executes it for you; you just include
    it in the tools list. When Claude needs to keep going after a search, the
    response comes back with stop_reason == "pause_turn" and you simply re-send.
  * A CLIENT tool (calculator) — Claude asks for it (stop_reason == "tool_use"),
    YOUR code runs the function and sends the result back.

Read run_agent() first, then come back up to the tools.
"""

import os
import ast
import operator

import anthropic
from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env

# Model names change over time. If this errors, check https://docs.claude.com
MODEL = "claude-sonnet-4-5"

MAX_STEPS = 8  # guardrail: never loop forever

SYSTEM_PROMPT = (
    "You are a careful research assistant. "
    "Use web_search for any fact that could be recent or that you are unsure "
    "about. Use the calculator for any exact arithmetic — never do math in your "
    "head. Give a concise final answer and cite the sources you used."
)


# ---------------------------------------------------------------------------
# CLIENT-SIDE TOOL: calculator (safe arithmetic via ast, never raw eval)
# ---------------------------------------------------------------------------
_ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression like '25000000000 * 83'."""
    try:
        tree = ast.parse(expression, mode="eval")
        return f"{expression} = {_safe_eval(tree.body)}"
    except Exception as exc:
        return f"Could not evaluate '{expression}': {exc}"


# Client tools we run ourselves. (web_search is a server tool — not in here.)
CLIENT_TOOL_FUNCTIONS = {"calculator": calculator}

# The tool list we send to Claude. Note the two different shapes:
TOOLS = [
    # SERVER tool: Anthropic runs the search. Just declare it.
    {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
    # CLIENT tool: we describe it; Claude asks; we run it.
    {
        "name": "calculator",
        "description": "Evaluate an exact arithmetic expression, e.g. '1234 * 56'. "
        "Use for any math instead of computing it yourself.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression using + - * / ** % and numbers.",
                }
            },
            "required": ["expression"],
        },
    },
]


def run_client_tool(name: str, tool_input: dict) -> str:
    func = CLIENT_TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Unknown tool: {name}"
    return func(**tool_input)


# ---------------------------------------------------------------------------
# THE AGENT LOOP
# ---------------------------------------------------------------------------
def run_agent(question: str) -> str:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # CASE A: a web search happened and Claude wants to continue thinking.
        # The server already ran the search; we just hand the turn back.
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            print(f"  [step {step}] web search ran (server-side), continuing...")
            continue

        # CASE B: Claude is asking us to run a CLIENT tool (e.g. calculator).
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":  # a client tool request
                    print(f"  [step {step}] calling {block.name}({block.input})")
                    result_text = run_client_tool(block.name, block.input)
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        # CASE C: no tool needed — this is the final answer.
        return "".join(b.text for b in response.content if b.type == "text").strip()

    return "Stopped: reached the maximum number of steps without finishing."


def main():
    print("Level 1 research agent ready. Ask a question (or 'quit').\n")
    while True:
        q = input("You: ").strip()
        if q.lower() in {"quit", "exit"}:
            break
        if q:
            print(f"\nAgent: {run_agent(q)}\n")


if __name__ == "__main__":
    main()
