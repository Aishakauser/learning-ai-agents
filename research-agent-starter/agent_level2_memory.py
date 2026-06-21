"""
LEVEL 2 — research_agent + MEMORY

Everything in Level 1 (web_search + calculator), PLUS the two kinds of memory
from Part 4.3 of the guide:

  1. SHORT-TERM memory = the conversation. In Level 1, every question started
     fresh. Here we KEEP the running `messages` list across turns, so the agent
     remembers what you said earlier in this session. (This is literally how
     chatbots "remember" — they re-send the whole conversation each time.)

  2. LONG-TERM memory = facts that survive AFTER you close the program. We give
     the agent a `remember` tool. When it learns something durable about you
     ("I live in Bangalore", "I prefer answers in bullet points"), it saves it
     to memory.json. On the next run, those facts are loaded back into the
     system prompt — so a brand-new session already knows them.

Try this:
  Run it. Say "Remember that I live in Bangalore and I'm learning Arabic."
  Quit. Run it again. Ask "what do you know about me?" — it still knows.
"""

import os
import ast
import json
import operator

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-5"
MAX_STEPS = 8
MEMORY_FILE = "memory.json"  # long-term memory lives here, on disk


# ---------------------------------------------------------------------------
# LONG-TERM MEMORY helpers (just a JSON list of fact strings)
# ---------------------------------------------------------------------------
def load_memory() -> list:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return []


def save_fact(fact: str) -> str:
    """The agent calls this (via the 'remember' tool) to store a durable fact."""
    facts = load_memory()
    if fact not in facts:
        facts.append(fact)
        with open(MEMORY_FILE, "w") as f:
            json.dump(facts, f, indent=2)
    return f"Saved to long-term memory: {fact}"


def build_system_prompt() -> str:
    base = (
        "You are a careful, friendly research assistant. "
        "Use web_search for recent or uncertain facts. Use the calculator for "
        "exact math. When the user tells you something durable about themselves "
        "or their preferences, call the 'remember' tool to save it. "
        "Cite sources in your final answer."
    )
    facts = load_memory()
    if facts:
        base += "\n\nWhat you already know about this user:\n" + "\n".join(
            f"- {fact}" for fact in facts
        )
    return base


# ---------------------------------------------------------------------------
# CLIENT-SIDE TOOLS: calculator + remember
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
    try:
        tree = ast.parse(expression, mode="eval")
        return f"{expression} = {_safe_eval(tree.body)}"
    except Exception as exc:
        return f"Could not evaluate '{expression}': {exc}"


def remember(fact: str) -> str:
    return save_fact(fact)


CLIENT_TOOL_FUNCTIONS = {"calculator": calculator, "remember": remember}

TOOLS = [
    {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
    {
        "name": "calculator",
        "description": "Evaluate an exact arithmetic expression, e.g. '1234 * 56'.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    {
        "name": "remember",
        "description": "Save a durable fact about the user or their preferences to "
        "long-term memory so it is remembered in future sessions. Use only for "
        "lasting facts, not one-off chit-chat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "The fact to remember."}
            },
            "required": ["fact"],
        },
    },
]


def run_client_tool(name: str, tool_input: dict) -> str:
    func = CLIENT_TOOL_FUNCTIONS.get(name)
    return func(**tool_input) if func else f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# THE LOOP — note `messages` is now passed IN and OUT to persist the chat
# ---------------------------------------------------------------------------
def run_agent(messages: list) -> str:
    client = anthropic.Anthropic()
    system_prompt = build_system_prompt()  # rebuilt each turn so new facts apply

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=1024, system=system_prompt,
            tools=TOOLS, messages=messages,
        )

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [step {step}] calling {block.name}({block.input})")
                    result_text = run_client_tool(block.name, block.input)
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        answer = "".join(b.text for b in response.content if b.type == "text").strip()
        # Record the assistant's final answer so it's part of short-term memory.
        messages.append({"role": "assistant", "content": answer})
        return answer

    return "Stopped: reached the maximum number of steps."


def main():
    print("Level 2 agent (with memory) ready. Ask a question (or 'quit').\n")
    # This single list IS the short-term memory — we keep appending to it.
    messages = []
    while True:
        q = input("You: ").strip()
        if q.lower() in {"quit", "exit"}:
            break
        if not q:
            continue
        messages.append({"role": "user", "content": q})
        print(f"\nAgent: {run_agent(messages)}\n")


if __name__ == "__main__":
    main()
