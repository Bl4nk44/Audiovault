---
name: memory-bank-protocol
description: Teaches the agent to use memory-bank/ as single source of truth and persist context between sessions
---

# Memory Bank Protocol Skill

## 🧠 Purpose

This skill makes you treat `memory-bank/` as your **only persistent memory**. You have NO other memory between sessions. Every session starts fresh unless you read these files.

## 📂 Memory Bank Architecture

### Location
`memory-bank/` (root of the project)

### Core Files (MANDATORY READING ORDER)

When starting ANY task or session, you MUST read these files IN THIS EXACT ORDER:

1. **`memory-bank/core/current-state.md`** – 🎯 **THE NOW**
   - What is currently happening
   - Active development phase
   - Current sprint tasks
   - Known issues

2. **`memory-bank/core/projectbrief.md`** – 📋 **THE MISSION**
   - What we're building and why
   - Vision and goals
   - Target users
   - Success metrics

3. **`memory-bank/core/productContext.md`** – 👥 **THE USER**
   - User personas
   - Pain points and goals
   - User journey
   - Market context

4. **`memory-bank/technical/techContext.md`** – 🔧 **THE TOOLS**
   - Technology stack
   - Architecture overview
   - Configuration files
   - Environment setup

5. **`memory-bank/technical/systemPatterns.md`** – 🏗️ **THE PATTERNS**
   - Architecture guidelines
   - Code patterns
   - Best practices
   - Testing strategies

6. **`memory-bank/core/progress.md`** – 📊 **THE HISTORY**
   - Completed milestones
   - Recent work
   - Metrics and achievements
   - Timeline

7. **`memory-bank/NOTES_NEXT_SESSION.md`** – 📝 **THE HANDOVER**
   - Specific instructions for THIS session
   - Context from last session
   - Pending tasks
   - Important reminders

## ✅ Mandatory Rules

### Rule 1: Boot Context
**BEFORE doing ANYTHING, read all memory-bank files in the order listed above.**

Example start of session:
```
User: "Add a new feature to import from Bandcamp"

Your response:
1. Read memory-bank/core/current-state.md
2. Read memory-bank/core/projectbrief.md
3. Read memory-bank/core/productContext.md
4. Read memory-bank/technical/techContext.md
5. Read memory-bank/technical/systemPatterns.md
6. Read memory-bank/core/progress.md
7. Read memory-bank/NOTES_NEXT_SESSION.md
8. NOW understand the task and respond appropriately
```

### Rule 2: Date Verification
**ALWAYS verify the current date before updating any memory-bank documents.**

Incorrect dates in documents cause context confusion.

### Rule 3: Update Protocol

**When making changes to the project:**

1. **Update `current-state.md`** if:
   - Starting a new task
   - Changing development phase
   - Discovering new issues

2. **Update `progress.md`** if:
   - Completing a milestone
   - Finishing a feature
   - Recording metrics

3. **Update `NOTES_NEXT_SESSION.md`** if:
   - Leaving context for next session
   - Documenting decisions made
   - Noting challenges encountered

### Rule 4: Session Closing Protocol

When the user says "finish session", "end session", "done for today", or similar:

1. **Update `current-state.md`**
   - Reflect the latest status of tasks
   - Add any new known issues
   - Update active sprint items

2. **Update `progress.md`**
   - Log completed milestones from this session
   - Update metrics if applicable
   - Add timestamp for recent work

3. **Rewrite `NOTES_NEXT_SESSION.md`**
   - Clear instructions for the "next you"
   - Context about what was done this session
   - What to continue working on
   - Any important decisions or blockers

4. **Cleanup**
   - Remove temporary files
   - Clean up debug logs
   - Ensure code is in working state

### Rule 5: Language Usage

- **Code, comments, and memory-bank files**: ALWAYS in English
- **User-facing UI**: Polish (as per project i18n)
- **Commit messages**: English
- **Documentation**: English

## 🚨 Anti-Patterns (DO NOT DO THIS)

❌ **Don't assume context from previous conversations** – You don't remember them  
❌ **Don't skip reading memory-bank files** – They are your only memory  
❌ **Don't update files without verifying date** – Causes temporal confusion  
❌ **Don't end session without updating handover notes** – Next session will be lost  
❌ **Don't write code that contradicts systemPatterns.md** – Architectural consistency matters  
❌ **Don't add features without checking projectbrief.md** – Stay aligned with mission  

## 📝 Example Workflow

### Starting a New Feature

```markdown
1. User requests: "Add Bandcamp integration"

2. Agent reads memory-bank files (1-7 in order)

3. Agent checks:
   - Is this aligned with projectbrief.md mission? ✓
   - Does current-state.md mention this? (check priority)
   - What patterns from systemPatterns.md apply?
   - Are there similar features in progress.md?

4. Agent implements feature following patterns

5. Agent updates:
   - current-state.md: Add task to active list
   - progress.md: Mark milestone when complete
   - NOTES_NEXT_SESSION.md: Note next steps if unfinished
```

### Debugging an Issue

```markdown
1. User reports: "Download fails for Spotify playlists"

2. Agent reads memory-bank files (especially current-state for known issues)

3. Agent checks:
   - Is this a known issue in current-state.md?
   - What's the download architecture in techContext.md?
   - What patterns apply from systemPatterns.md?

4. Agent investigates and fixes

5. Agent updates:
   - current-state.md: Remove from known issues if fixed
   - progress.md: Log the fix
   - NOTES_NEXT_SESSION.md: Document root cause for future reference
```

## 📊 Success Indicators

- Agent never asks "What is Audiovault?" after reading projectbrief.md
- Agent follows architecture patterns from systemPatterns.md
- Agent references current-state.md when prioritizing tasks
- Context persists between sessions via NOTES_NEXT_SESSION.md
- Agent updates memory-bank appropriately as work progresses

## 🔗 Related Files

- All files in `memory-bank/` directory
- `.agent/skills/audiovault-developer/SKILL.md` for project-specific knowledge
- `.agent/workflows/*.md` for procedural tasks

---

**Remember:** You are only as smart as the Memory Bank. Keep it updated, and it will keep you context-aware.
