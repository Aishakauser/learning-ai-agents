# Learning AI Agents

A beginner-friendly path to understanding and building AI agents — written in
plain language, with diagrams and runnable code. No prior AI experience needed.

It has two parts: a **guide** that explains every concept from the ground up, and
a **starter project** that lets you build a real agent by hand and watch it work.

## Contents

### 📘 `docs/` — learn the concepts
- **`Building-AI-Agents-Complete-Guide.md`** — a complete, jargon-free guide in 8
  parts: the developer toolkit → tech stacks → how LLMs work (tokens, neural
  networks, embeddings) → turning a chatbot into an agent (tools, memory, RAG, the
  agent loop) → making agents intelligent (planning, reasoning, guardrails) →
  frameworks (LangChain, LangGraph, Claude Agent SDK, MCP) → multi-agent systems &
  Deep Agents → a first project. Includes a glossary.
- **`AI-Agents-Concept-Map.html`** — a one-page visual map showing how all the
  concepts connect. Open it in any browser.

### 🛠️ `research-agent-starter/` — build a real agent
A tiny agent built **by hand** (no framework) so you can see the
think → act → observe loop run. Three levels you build up gradually:

| File | Adds |
|---|---|
| `agent.py` | **Level 1** — web search (Claude's built-in) + a calculator |
| `agent_level2_memory.py` | **Level 2** — remembers the chat + saves durable facts |
| `agent_level3_rag.py` | **Level 3** — answers from your own documents (RAG) |

The big lesson: the agent loop barely changes between levels — you only add
capabilities. See `research-agent-starter/README.md` for full setup.

## Quick start

```bash
cd research-agent-starter
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # paste your key from console.anthropic.com
python agent.py
```

## The one-line idea

> An **agent** = an **LLM** + a **loop** + **tools** + **memory** + **guardrails**.

Everything in the guide is a variation on that sentence.

---

*Built as a learning project. The code is original; the guide is written for people
new to AI agents. Contributions and corrections welcome.*

## License

MIT — free to use, learn from, and share.
