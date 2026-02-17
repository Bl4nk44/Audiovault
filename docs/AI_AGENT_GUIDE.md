# AI Agent Integration Guide

## Overview

Audiovault includes an integrated AI agent configuration optimized for development assistance. The agent uses a memory-bank system to maintain context across sessions, reducing token usage and improving response quality.

## Features

### Memory Bank System
- **Persistent Context**: Project knowledge maintained across sessions
- **Token Optimization**: Frequently referenced information stored, not repeated
- **Pattern Recognition**: Learned solutions to common problems
- **Specialized Skills**: Domain-specific knowledge loaded on demand

### Agent Capabilities
- Backend development (Python/FastAPI)
- Frontend development (React/TypeScript)
- Platform integrations
- Code review and quality assurance
- Bug diagnosis and fixing
- Architecture decisions

## Quick Start

### For AI Assistants

1. **Start Every Session:**
   ```
   Read: .antigravity/memory-bank/core/current-state.md
   ```

2. **Load Relevant Skills:**
   - Backend task → `.antigravity/SKILLS/backend-specialist.md`
   - Frontend task → `.antigravity/SKILLS/frontend-specialist.md`
   - Any task → `.antigravity/SKILLS/audiovault-developer.md`

3. **Follow Workflows:**
   - New feature → `.antigravity/WORKFLOWS/feature-development.md`
   - Bug fix → `.antigravity/WORKFLOWS/bug-fix.md`
   - Code review → `.antigravity/WORKFLOWS/code-review.md`

4. **End Every Session:**
   ```
   Update: .antigravity/memory-bank/core/current-state.md
   ```

### For Developers

1. **Update Current State:**
   ```bash
   # Edit after completing work
   vim .antigravity/memory-bank/core/current-state.md
   ```

2. **Add Common Issues:**
   ```bash
   # Document solutions to new problems
   vim .antigravity/memory-bank/patterns/common-issues.md
   ```

3. **Record Design Decisions:**
   ```bash
   # Explain why choices were made
   vim .antigravity/memory-bank/patterns/design-decisions.md
   ```

## Directory Structure

```
.antigravity/
├── agent.yaml                 # Main configuration
├── memory-bank/               # Persistent memory
│   ├── core/                  # Always-loaded context
│   │   ├── current-state.md   # 🔄 Update frequently
│   │   ├── projectbrief.md    # 🔒 Rarely changes
│   │   ├── productContext.md  # 🔒 Rarely changes
│   │   └── techContext.md     # 🔄 Update with stack changes
│   └── patterns/              # Learned knowledge
│       ├── common-issues.md   # 🔄 Add new issues
│       └── design-decisions.md # 🔄 Add new decisions
├── SKILLS/                    # Agent capabilities
│   ├── memory-bank-protocol.md
│   ├── audiovault-developer.md
│   ├── backend-specialist.md
│   └── frontend-specialist.md
└── WORKFLOWS/                 # Standard processes
    ├── feature-development.md
    ├── bug-fix.md
    └── code-review.md
```

## Memory Management

### What to Store
✅ **Good for Memory:**
- Project architecture overview
- Technology stack and versions
- Coding conventions and patterns
- Common issues and solutions
- Design decisions and rationale
- User preferences

❌ **Bad for Memory:**
- Current file contents (read fresh)
- Active bugs (check GitHub issues)
- Recent commits (use git log)
- Temporary decisions
- Large code blocks (link to files instead)

### Update Frequency

| File | When to Update |
|------|----------------|
| `current-state.md` | End of every session |
| `common-issues.md` | When new issue solved |
| `design-decisions.md` | When important decision made |
| `techContext.md` | When stack/architecture changes |
| `projectbrief.md` | Rarely (major direction change) |
| `productContext.md` | When user personas change |

## Usage Examples

### Example 1: Adding a New Feature

**User Request:** "Add support for Apple Music integration"

**Agent Process:**
1. 📄 Read `current-state.md` - knows current project state
2. 📚 Load `audiovault-developer.md` - knows platform integration patterns
3. 📖 Follow `feature-development.md` - knows development workflow
4. 📑 Reference `techContext.md` - knows tech stack details
5. ⚙️ Implement feature following established patterns
6. ✍️ Update `current-state.md` with progress

**Benefits:**
- No repeated questions about project structure
- Consistent with existing integrations
- Follows established patterns
- Progress tracked for next session

### Example 2: Fixing a Bug

**User Report:** "Downloads fail for region-locked videos"

**Agent Process:**
1. 📄 Read `current-state.md` - context loaded
2. 🔍 Check `common-issues.md` - similar issue?
3. 📖 Follow `bug-fix.md` - systematic approach
4. 🔧 Implement fix with fallback strategy
5. ✅ Add regression test
6. ✍️ Update `common-issues.md` with solution

**Benefits:**
- Checks known issues first
- Follows systematic debugging process
- Documents solution for future
- Prevents similar bugs

### Example 3: Code Review

**Pull Request:** "feat: Add Spotify album import"

**Agent Process:**
1. 📚 Load `audiovault-developer.md` - knows domain
2. 📚 Load `backend-specialist.md` - knows Python/FastAPI
3. 📖 Follow `code-review.md` - systematic checklist
4. 🔍 Check against established patterns
5. ✅ Provide specific, actionable feedback

**Benefits:**
- Consistent review criteria
- Checks domain-specific concerns
- References existing patterns
- Constructive feedback

## Configuration

### agent.yaml

Key configuration options:

```yaml
memory:
  enabled: true
  strategy: token-optimized
  max_context_tokens: 15000
  
task_routing:
  backend:
    skills: [backend-specialist.md, audiovault-developer.md]
    workflows: [feature-development.md, bug-fix.md]
  
guardrails:
  require_memory_check: true
  checks:
    - no_blocking_in_async: true
    - type_hints_required: true
```

### Customization

Edit `agent.yaml` to:
- Adjust token budgets
- Add new skills
- Define custom workflows
- Configure guardrails
- Set integration preferences

## Best Practices

### For AI Agents

1. **Always Check Memory First**
   - Don't ask questions already answered in memory
   - Reference memory files in explanations

2. **Update Memory at Session End**
   - Current state
   - New learnings
   - Open questions

3. **Follow Workflows**
   - Consistency across sessions
   - Complete processes
   - Quality gates

4. **Load Relevant Skills**
   - Don't load everything
   - Task-specific knowledge
   - Reduce token usage

### For Developers

1. **Keep Memory Current**
   - Update after major changes
   - Document decisions
   - Record solutions

2. **Be Specific**
   - Concrete examples
   - Code snippets
   - Clear patterns

3. **Link Related Info**
   - Cross-reference files
   - Avoid duplication
   - Maintain consistency

4. **Review Regularly**
   - Weekly check
   - Archive outdated info
   - Update stack changes

## Troubleshooting

### Agent Asks Repeated Questions

**Problem:** Agent doesn't remember previous answers

**Solution:**
```bash
# Add answer to relevant memory file
vim .antigravity/memory-bank/core/techContext.md
# or
vim .antigravity/memory-bank/patterns/common-issues.md
```

### Agent Doesn't Follow Patterns

**Problem:** Code doesn't match existing style

**Solution:**
- Check if correct skill is loaded
- Update skill with clearer examples
- Add to `audiovault-developer.md`

### High Token Usage

**Problem:** Context size too large

**Solution:**
- Remove verbosity from memory files
- Use bullet points over paragraphs
- Link to code instead of pasting
- Archive old patterns

### Outdated Responses

**Problem:** Agent suggests old approaches

**Solution:**
```bash
# Update technical context
vim .antigravity/memory-bank/core/techContext.md

# Update design decisions
vim .antigravity/memory-bank/patterns/design-decisions.md
```

## CI/CD Integration

The project includes automated validation:

```yaml
# .github/workflows/agent-memory-validator.yml
- Validates memory file structure
- Checks for secrets
- Verifies YAML syntax
- Ensures markdown quality
```

## Metrics

Track agent effectiveness:
- Token usage per session
- Questions asked vs. answered from memory
- Pattern reuse frequency
- Session continuity score

## Contributing

When contributing agent improvements:

1. **Add New Skills:**
   ```bash
   # Create skill file
   touch .antigravity/SKILLS/new-skill.md
   
   # Register in agent.yaml
   vim .antigravity/agent.yaml
   ```

2. **Document Patterns:**
   - Add to `common-issues.md`
   - Explain in `design-decisions.md`
   - Include code examples

3. **Test Changes:**
   - Verify memory structure
   - Check CI validation
   - Test with actual agent

## Resources

- [Google Antigravity Documentation](https://antigravity.google/docs)
- [Memory Bank Protocol](../.antigravity/SKILLS/memory-bank-protocol.md)
- [Agent Configuration](../.antigravity/agent.yaml)
- [Audiovault Developer Guide](../.antigravity/SKILLS/audiovault-developer.md)

## Support

For issues with agent configuration:
- GitHub Issues: Tag with `agent` label
- Discussions: AI Agent category
- Documentation: This file and `.antigravity/README.md`

## Version History

- **1.0.0** (2026-02-17): Initial agent integration
  - Memory bank structure
  - Core skills (4)
  - Standard workflows (3)
  - CI validation
