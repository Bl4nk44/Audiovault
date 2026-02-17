# Antigravity AI Agent Configuration

This directory contains the configuration and memory bank for the Audiovault AI agent.

## Structure

```
.antigravity/
├── agent.yaml                 # Main agent configuration
├── README.md                  # This file
├── memory-bank/               # Persistent memory storage
│   ├── core/                  # Always-loaded context
│   │   ├── current-state.md   # Current work state
│   │   ├── projectbrief.md    # Project mission and goals
│   │   ├── productContext.md  # User personas and use cases
│   │   └── techContext.md     # Technical architecture
│   └── patterns/              # Learned patterns
│       ├── common-issues.md   # Known problems and solutions
│       ├── design-decisions.md # Why things are done this way
│       └── api-patterns.md    # Common API usage patterns
├── SKILLS/                    # Agent capabilities
│   ├── memory-bank-protocol.md # Memory management
│   ├── audiovault-developer.md # Domain expertise
│   ├── backend-specialist.md   # Python/FastAPI
│   └── frontend-specialist.md  # React/TypeScript
└── WORKFLOWS/                 # Standard processes
    ├── feature-development.md # Adding new features
    ├── bug-fix.md            # Fixing bugs
    └── code-review.md        # Reviewing code
```

## Purpose

This configuration enables the AI agent to:

1. **Remember Context**: Maintain project knowledge across sessions
2. **Reduce Token Usage**: Store frequently referenced information
3. **Improve Consistency**: Follow established patterns and workflows
4. **Specialize**: Load domain-specific skills as needed
5. **Optimize Performance**: Cache and reuse information

## How It Works

### Session Start
1. Agent reads `memory-bank/core/current-state.md`
2. Loads relevant skills based on task type
3. References workflows for standard processes
4. Confirms understanding with user

### During Work
1. References memory-bank instead of asking repeated questions
2. Follows established patterns and conventions
3. Uses workflows for consistency
4. Updates current-state.md with progress

### Session End
1. Updates `current-state.md` with:
   - What was accomplished
   - What's in progress
   - What's next
   - Any blockers
2. Saves new learnings to pattern files
3. Summarizes for user

## Benefits

### For Users
- Faster responses (less context gathering)
- Consistent code quality
- Better continuity between sessions
- Fewer repeated explanations

### For Agent
- Reduced token usage (stored context)
- Better decision making (learned patterns)
- Specialized knowledge available
- Clear processes to follow

## Memory Files

### Core (Always Loaded)
Essential project information loaded at every session start.

### Patterns (On Demand)
Lesson learned, common issues, and design rationale loaded when relevant.

### Skills (Task-Specific)
Specialized knowledge loaded based on current task:
- Backend work → `backend-specialist.md`
- Frontend work → `frontend-specialist.md`
- Any Audiovault work → `audiovault-developer.md`

### Workflows (Process-Specific)
Step-by-step guides for common processes:
- New feature → `feature-development.md`
- Bug report → `bug-fix.md`
- PR review → `code-review.md`

## Token Optimization

### What Gets Stored (Not Re-explained)
- Project architecture
- Technology stack
- Coding conventions
- User preferences
- Common patterns
- Known issues

### What's Always Fresh (Never Cached)
- Current file contents
- Active bugs/issues
- Recent commits
- User's immediate request

## Maintenance

### Daily
- Update `current-state.md` at session end

### Weekly
- Review pattern files for relevance
- Archive outdated information
- Update common-issues.md with new problems

### Monthly
- Review all memory files
- Update techContext.md if stack changes
- Clean up stale entries

## Configuration

Edit `agent.yaml` to customize:
- Memory file locations
- Token budgets
- Task routing
- Guardrails
- Integration settings

## Best Practices

1. **Keep Files Concise**: Use bullet points and headers
2. **Update Regularly**: Memory degrades if stale
3. **Be Specific**: Vague context wastes tokens
4. **Use Examples**: Code snippets better than descriptions
5. **Link Related Info**: Cross-reference memory files

## Troubleshooting

### Agent Asks Repeated Questions
→ Update relevant memory file with the answer

### Agent Doesn't Follow Patterns
→ Check if correct skill/workflow is loaded

### High Token Usage
→ Review memory files, remove verbosity

### Outdated Responses
→ Update techContext.md or current-state.md

## Example Usage

**User:** "Add a new platform integration"

**Agent Process:**
1. Reads `current-state.md` (knows project state)
2. Loads `audiovault-developer.md` (knows platform integration patterns)
3. Follows `feature-development.md` (knows process)
4. References `techContext.md` (knows tech stack)
5. Implements feature following established patterns
6. Updates `current-state.md` with progress

## Version History

- **1.0.0** (2026-02-17): Initial configuration
  - Memory bank structure
  - Core skills defined
  - Standard workflows documented
