"""
LEVEL 3 — research_agent + MEMORY + RAG (read your own documents)

Everything in Level 2, PLUS Retrieval-Augmented Generation (Part 4.4).

The new idea: the agent can answer from YOUR documents — files it never saw in
training. We do this exactly as the guide describes:

  ONE-TIME PREP (ingest):
    read files in ./docs  ->  split into chunks  ->  store in a vector database
    (Chroma turns each chunk into an embedding for you — no extra API key).

  EVERY RELEVANT QUESTION:
    we expose a `search_documents` tool. When the agent thinks your docs might
    hold the answer, it calls it; Chroma finds the chunks closest in MEANING to
    the question; those chunks go back to the agent, which answers from them.

So RAG here is just... another tool. That's the elegant part: the loop didn't
change at all between Level 1 and Level 3 — we only added capabilities.

Setup note: the FIRST run downloads a small (~80MB) embedding model that Chroma
uses locally. After that it's instant and fully offline for search.

Try this:
  A sample file is in ./docs. Ask: "What is Project Lighthouse's launch date?"
  The answer is ONLY in your docs, not on the web — so you know RAG worked.
"""

import os
import ast
import json
import glob
import operator

import anthropic
import chromadb
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-5"
MAX_STEPS = 8
MEMORY_FILE = "memory.json"
DOCS_FOLDER = "docs"
CHUNK_SIZE = 600  # characters per chunk (simple, good enough for a starter)


# ---------------------------------------------------------------------------
# RAG SETUP — build the vector database from ./docs
# ---------------------------------------------------------------------------
def chunk_text(text: str, size: int = CHUNK_SIZE) -> list:
    """Split text into overlapping-ish chunks by paragraphs, then by size."""
    chunks, current = [], ""
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) < size:
            current += " " + para
        else:
            if current:
                chunks.append(current.strip())
            current = para
    if current:
        chunks.append(current.strip())
    return chunks


def build_vector_db():
    """Read ./docs, chunk every file, and load it into an in-memory Chroma DB."""
    client = chromadb.EphemeralClient()  # fresh each run; simple and predictable
    collection = client.create_collection("my_docs")

    files = glob.glob(os.path.join(DOCS_FOLDER, "*"))
    docs, ids, metas = [], [], []
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        for i, chunk in enumerate(chunk_text(text)):
            docs.append(chunk)
            ids.append(f"{os.path.basename(path)}::{i}")
            metas.append({"source": os.path.basename(path)})

    if docs:
        # Chroma creates the embeddings for us using its built-in local model.
        collection.add(documents=docs, ids=ids, metadatas=metas)
    print(f"  [rag] indexed {len(docs)} chunks from {len(files)} file(s) in ./{DOCS_FOLDER}")
    return collection


# Built once at startup.
COLLECTION = build_vector_db()


def search_documents(query: str) -> str:
    """Find the chunks in YOUR docs most similar in meaning to the query."""
    if COLLECTION.count() == 0:
        return "No documents are indexed. Add files to the ./docs folder."
    res = COLLECTION.query(query_texts=[query], n_results=3)
    chunks = res.get("documents", [[]])[0]
    sources = [m.get("source") for m in res.get("metadatas", [[]])[0]]
    if not chunks:
        return "No relevant passages found in your documents."
    return "\n\n".join(f"[from {src}] {c}" for c, src in zip(chunks, sources))


# ---------------------------------------------------------------------------
# LONG-TERM MEMORY (same as Level 2)
# ---------------------------------------------------------------------------
def load_memory() -> list:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return []


def save_fact(fact: str) -> str:
    facts = load_memory()
    if fact not in facts:
        facts.append(fact)
        with open(MEMORY_FILE, "w") as f:
            json.dump(facts, f, indent=2)
    return f"Saved to long-term memory: {fact}"


def build_system_prompt() -> str:
    base = (
        "You are a careful research assistant with three information sources: "
        "your own knowledge, web_search for recent/uncertain facts, and "
        "search_documents for the user's PRIVATE documents. Prefer search_documents "
        "for anything that sounds specific to the user, their projects, or their "
        "files. Use the calculator for exact math. Save durable user facts with "
        "the 'remember' tool. Always cite where information came from."
    )
    facts = load_memory()
    if facts:
        base += "\n\nWhat you already know about this user:\n" + "\n".join(
            f"- {fact}" for fact in facts
        )
    return base


# ---------------------------------------------------------------------------
# CLIENT-SIDE TOOLS
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


CLIENT_TOOL_FUNCTIONS = {
    "calculator": calculator,
    "remember": remember,
    "search_documents": search_documents,
}

TOOLS = [
    {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
    {
        "name": "search_documents",
        "description": "Search the user's private documents (in ./docs) for "
        "passages relevant to a query. Use this for anything specific to the "
        "user, their projects, notes, or files.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
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
        "description": "Save a durable fact about the user to long-term memory.",
        "input_schema": {
            "type": "object",
            "properties": {"fact": {"type": "string"}},
            "required": ["fact"],
        },
    },
]


def run_client_tool(name: str, tool_input: dict) -> str:
    func = CLIENT_TOOL_FUNCTIONS.get(name)
    return func(**tool_input) if func else f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# THE LOOP (identical structure to Level 2 — only the toolbox grew)
# ---------------------------------------------------------------------------
def run_agent(messages: list) -> str:
    client = anthropic.Anthropic()
    system_prompt = build_system_prompt()

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
        messages.append({"role": "assistant", "content": answer})
        return answer

    return "Stopped: reached the maximum number of steps."


def main():
    print("\nLevel 3 agent (memory + RAG) ready. Ask a question (or 'quit').\n")
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
