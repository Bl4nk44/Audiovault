---
name: memory-bank-protocol
description: Hybrid memory system combining OpenMemory MCP (semantic persistence) with .agent/memory-bank/ static files (structural context). OpenMemory is the primary dynamic memory; memory-bank files are the structural foundation.
---

# Memory Protocol – Hybrid (OpenMemory + Memory Bank)

## 🧠 Architecture Overview

This project uses **two complementary memory layers**:

| Layer | Source | What it stores | When used |
|-------|--------|----------------|-----------|
| **OpenMemory** (primary) | MCP tools: `openmemory_*` | Decisions, bugs, progress, recent changes | Dynamic – updated every session |
| **Memory Bank** (structural) | `.agent/memory-bank/` files | Project brief, product context, tech stack, patterns | Static – updated when architecture changes |

> ⚠️ **OpenMemory is the primary source of truth for recent context.**
> Memory-bank files provide structural/architectural foundation that changes rarely.

---

## 📂 Memory Bank Files (Structural Layer)

### Location: `.agent/memory-bank/` (NOT `memory-bank/` at project root)

#### Core Files (always load at session start)

1. **`.agent/memory-bank/core/current-state.md`** – Active tasks, current phase, known issues
2. **`.agent/memory-bank/core/projectbrief.md`** – Mission, vision, goals, success metrics
3. **`.agent/memory-bank/core/productContext.md`** – User personas, pain points, user journey
4. **`.agent/memory-bank/core/techContext.md`** – Tech stack, architecture, environment setup

#### Pattern Files (load when relevant to the task)

5. **`.agent/memory-bank/patterns/api-patterns.md`** – API design patterns, endpoint conventions
6. **`.agent/memory-bank/patterns/common-issues.md`** – Known recurring issues, debugging notes
7. **`.agent/memory-bank/patterns/design-decisions.md`** – Architectural decisions and their rationale

---

## 🔌 OpenMemory MCP Tools

All six tools are enabled via the `openmemory` MCP server in Antigravity:

| Tool | Purpose |
|------|---------|
| `openmemory_query` | Search semantic/episodic memories by keyword |
| `openmemory_store` | Persist a new memory (decision, fix, progress) |
| `openmemory_reinforce` | Boost salience of an important existing memory |
| `openmemory_delete` | Remove an outdated or incorrect memory |
| `openmemory_list` | List the most recent memories |
| `openmemory_get` | Fetch a single memory by its identifier |

---

## 🚀 Session Start Protocol (MANDATORY)

**Execute this BEFORE responding to any user task:**

### Step 1 – Query OpenMemory (dynamic context)

```
openmemory_query("Audiovault current state progress recent decisions")
openmemory_query("active tasks blockers recent changes")
```

### Step 2 – Read core memory-bank files (structural context)

```
Read: .agent/memory-bank/core/current-state.md
Read: .agent/memory-bank/core/projectbrief.md
Read: .agent/memory-bank/core/techContext.md
```

Load pattern files only when the task touches API design, architecture, or known issues.

### Step 3 – Synthesize

Combine OpenMemory results (recent) with memory-bank context (structural) before responding.
Do NOT ask the user for context that either source already provides.

---

## 💾 During-Session Storage Protocol

**Call `openmemory_store` immediately when:**

- A significant architectural or design decision is made
- A bug is identified or fixed
- A new pattern or convention is established
- A feature is completed or blocked
- Important configuration detail is discovered

**Recommended memory format:**

```
[YYYY-MM-DD] [CATEGORY]: <clear, searchable, self-contained description>
```

**Categories:** `DECISION` · `BUG_FIX` · `FEATURE` · `BLOCKER` · `PATTERN` · `CONFIG` · `SESSION_SUMMARY`

**Example:**

```
openmemory_store(
  content="[2026-02-23] DECISION: Switched download queue from threading to asyncio.Queue. Reason: eliminates blocking in FastAPI event loop. File: backend/services/download_service.py",
  metadata={"sector": "procedural", "project": "audiovault"}
)
```

---

## 🔚 Session End Protocol

When user says "finish session", "end session", "done for today", or similar:

### 1. Store session summary to OpenMemory

```
openmemory_store(
  content="[DATE] SESSION_SUMMARY: <what was accomplished, key decisions, what to continue next session>",
  metadata={"sector": "episodic", "project": "audiovault"}
)
```

### 2. Update memory-bank ONLY if structural context changed

Update these files only when the underlying architecture/context shifts – not after every session:

- `.agent/memory-bank/core/current-state.md` – if active tasks or development phase changed
- `.agent/memory-bank/core/techContext.md` – ONLY if tech stack changed
- `.agent/memory-bank/patterns/design-decisions.md` – ONLY if a new architectural pattern was established
- `.agent/memory-bank/patterns/common-issues.md` – if a new recurring issue was discovered

---

## ✅ Rules

### Rule 1: OpenMemory First
Always query OpenMemory **before** reading memory-bank files. OpenMemory has the most recent context.

### Rule 2: Store Decisions Immediately
Do not wait until session end. Store important decisions and bug fixes as they happen during the session.

### Rule 3: Correct Paths
Memory bank is at **`.agent/memory-bank/`** – never `memory-bank/` at the project root (that directory does not exist).

### Rule 4: Language
- Code, comments, memory-bank files, OpenMemory entries → **English**
- User-facing UI text → **Polish** (project uses i18n)
- Commit messages → **English**

### Rule 5: Date Verification
Always verify the current date before storing memories or updating any files to avoid temporal confusion.

---

## 🚨 Anti-Patterns (DO NOT DO THIS)

❌ Skipping `openmemory_query` at session start – you will miss recent context
❌ Using path `memory-bank/` – correct path is `.agent/memory-bank/`
❌ Treating memory-bank files as the ONLY memory – OpenMemory is the primary dynamic layer
❌ Storing everything in memory-bank markdown instead of OpenMemory (wrong layer for dynamic data)
❌ Ending session without storing a summary to OpenMemory
❌ Asking the user for context that OpenMemory or memory-bank already contains
❌ Hardcoding the OpenMemory API key in any file – use `OM_API_KEY` env var

---

## 📊 Memory Layer Decision Guide

| Information type | Store where? |
|-----------------|--------------|
| What I decided in today's session | `openmemory_store` |
| Bug found or fixed today | `openmemory_store` |
| Current sprint/task progress | `openmemory_store` |
| Project tech stack & architecture | `.agent/memory-bank/core/techContext.md` |
| API design conventions | `.agent/memory-bank/patterns/api-patterns.md` |
| Project mission and vision | `.agent/memory-bank/core/projectbrief.md` |
| Recurring known issues | `.agent/memory-bank/patterns/common-issues.md` |

**Principle:** OpenMemory remembers *what happened*. Memory-bank files remember *who we are*.

---

## 🔗 Related Files

- `.agent/agent.yaml` – full agent configuration including OpenMemory MCP endpoint
- `.agent/skills/audiovault-developer/SKILL.md` – project-specific knowledge
- `.agent/workflows/` – procedural task workflows
