# Skill: Memory Bank Protocol

## Purpose
Manage persistent memory across agent sessions to reduce token usage and maintain context.

## When to Use
- At the start of EVERY conversation
- After completing major tasks
- When context becomes stale
- Before ending a work session

## Protocol

### Session Start Routine
1. **Read** `.antigravity/memory-bank/core/current-state.md`
2. **Check** what was happening in last session
3. **Load** relevant context from other memory files
4. **Confirm** understanding with user

### During Work
1. **Reference** memory-bank instead of asking repeated questions
2. **Note** important decisions and patterns
3. **Track** progress on tasks

### Session End Routine
1. **Update** `current-state.md` with:
   - What was accomplished
   - What's in progress
   - What's next
   - Any blockers or questions
2. **Save** new learnings to relevant memory files
3. **Summarize** for user

## Memory File Structure

### Core (Always Check)
- `current-state.md`: Current work state, active tasks, next priorities
- `projectbrief.md`: Mission, vision, core features (rarely changes)
- `productContext.md`: User personas, use cases, feedback themes
- `techContext.md`: Architecture, stack, critical paths

### Patterns (Create as needed)
- `common-issues.md`: Frequent problems and solutions
- `design-decisions.md`: Why certain approaches were chosen
- `api-patterns.md`: Common API usage patterns
- `gotchas.md`: Non-obvious behaviors and edge cases

## Token Optimization Tips

### Store in Memory (Don't Re-explain)
- Project architecture and file structure
- Technology stack and versions
- Coding conventions and patterns
- User preferences and constraints

### Always Fresh (Don't Cache)
- Current file contents
- Active bugs/issues
- Recent commits
- User's immediate request

## Example Usage

**❌ Bad (No Memory)**
```
User: "Add a new endpoint"
Agent: "What framework are you using? What's your code style?"
```

**✅ Good (With Memory)**
```
User: "Add a new endpoint"
Agent: *reads techContext.md* "I'll add a FastAPI endpoint following your async SQLAlchemy pattern. Which service?"
```

## Maintenance
- Review memory files weekly
- Archive outdated content
- Keep files concise and scannable
- Use headings and lists for quick parsing
