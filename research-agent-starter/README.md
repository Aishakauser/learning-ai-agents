# Research Agent — Starter Project (3 levels)

A tiny, real AI agent built **by hand** (no framework) so you can see the
think → act → observe loop actually run. From Part 8 of *Building AI Agents — A
Complete Guide*.

It comes in three levels so you can build up gradually. Each level is a single,
heavily-commented file. The agent loop barely changes between them — you only add
capabilities. That's the whole lesson.

| File | What it adds | Concept (guide) |
|---|---|---|
| `agent.py` | **Level 1** — web search + calculator | Tools, the agent loop (Parts 4.2, 4.5) |
| `agent_level2_memory.py` | **Level 2** — remembers the chat + saves durable facts | Memory (Part 4.3) |
| `agent_level3_rag.py` | **Level 3** — answers from your own documents | RAG (Part 4.4) |

Web search uses **Claude's official built-in web search** — it runs on
Anthropic's servers and returns results with citations. Rock-solid, no extra key.

---

## Setup (about 5 minutes)

You need Python 3.9+. In this folder:

```bash
python -m venv .venv
source .venv/bin/activate          # Mac/Linux  (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env                # then paste your key from console.anthropic.com
python agent.py                     # Level 1
```

Type a question; type `quit` to exit. (For Level 1 and 2 you can skip installing
`chromadb` — it's only needed for Level 3.)

---

## Level 1 — `agent.py`

Claude decides on its own when to **search the web** and when to **calculate**,
looping until it can answer.

Try: *"What was NVIDIA's most recent annual revenue, and what is that in Indian
rupees?"* — watch it search twice, then use the calculator, then answer with
sources.

This file shows the **two kinds of tool** side by side:
- a **server tool** (`web_search`) — Anthropic runs it; when the model needs to
  continue after a search, the response comes back as `pause_turn` and you just
  re-send.
- a **client tool** (`calculator`) — the model asks (`tool_use`), *your* code runs
  the function and returns the result.

---

## Level 2 — `agent_level2_memory.py`

Adds both kinds of memory:

- **Short-term:** the conversation is kept across turns (the `messages` list is no
  longer reset each question), so it remembers what you said a moment ago.
- **Long-term:** a `remember` tool saves durable facts to `memory.json`. On the
  next run those facts load back into the system prompt — so a fresh session
  already knows them.

Try: say *"Remember that I live in Bangalore and I'm learning Arabic."* Quit. Run
again and ask *"What do you know about me?"* — it still knows. (Delete
`memory.json` to wipe its long-term memory.)

---

## Level 3 — `agent_level3_rag.py`

Adds **RAG** — answering from *your* documents. On startup it reads every file in
`./docs`, splits them into chunks, and loads them into a local **Chroma** vector
database (Chroma makes the embeddings for you — no extra API key). A new
`search_documents` tool lets the agent find the chunks closest in *meaning* to a
question.

A sample file (`docs/sample-notes.md`) is included. Try:
*"What is Project Lighthouse's launch date?"* — that fact exists **only** in your
docs and nowhere online, so a correct answer proves RAG worked. Then drop your own
`.txt`/`.md` files into `./docs` and ask about them.

> First run downloads a small (~80MB) embedding model that Chroma uses locally;
> after that, search is instant and offline.

The beautiful part: **the loop is identical to Level 2.** RAG is just another tool.

---

## How the code maps to the concepts

| In the guide | In the code |
|---|---|
| System prompt (Part 3.4) | `SYSTEM_PROMPT` / `build_system_prompt()` |
| Server vs client tools (Part 4.2) | `web_search` entry vs `calculator` entry in `TOOLS` |
| The agent loop (Part 4.5) | `run_agent` — the `for step in range(...)` loop |
| Short/long-term memory (Part 4.3) | `messages` list / `memory.json` + `remember` |
| RAG (Part 4.4) | `build_vector_db`, `search_documents` |
| Guardrail: loop cap (Part 5.3) | `MAX_STEPS` |
| Guardrail: safe tool (Part 8.3) | `calculator` uses `ast`, not raw `eval` |

---

## Things to try (turn reading into understanding)

1. **Watch it think.** Read the `[step N] calling ...` lines — that's the loop
   choosing tools.
2. **Add a tool.** Copy the `calculator` pattern (e.g. a `get_current_time` tool):
   add it to `TOOLS` and the tool-functions map. You won't touch the loop — that's
   the design's power.
3. **Break a guardrail.** Set `MAX_STEPS = 1` and ask something needing two steps;
   watch it stop safely.
4. **Change its personality.** Edit the system prompt to "answer in one sentence."
5. **Prove RAG.** In Level 3, ask about Project Lighthouse, then delete
   `docs/sample-notes.md` and ask again — it can no longer answer. That's RAG.

---

## Notes & caveats

- **Model name:** `MODEL` is set to a current Claude model. If you get a "model
  not found" error, check https://docs.claude.com for the latest string and update
  that one line.
- **Cost:** each question is a few short API calls — fractions of a cent. Web
  search has a small per-search fee. Set a spending limit in your Anthropic console
  while experimenting.
- **Your key is secret.** It lives only in `.env`, which `.gitignore` keeps out of
  git. `memory.json` and the Chroma data are also git-ignored.

---

## Where to go next

- Swap the hand-rolled Chroma setup for a hosted vector DB (Pinecone, Weaviate) as
  your document set grows.
- Add **evaluation** (Part 5.3): a small set of test questions with known answers,
  scored automatically, so you can tell if a change helped.
- Refactor onto the **Claude Agent SDK** or **LangGraph** — now you'll know exactly
  which plumbing they remove, because you built it here.
