# Growspace Manager Skills

This directory contains specialized skills for developing the Growspace Manager ecosystem.

## Available Skills

### 1. [Home Assistant Component Development](./ha-component-dev/SKILL.md)

**Purpose**: Expert guidance for developing the `growspace_manager` custom Home Assistant component.

**Key Topics**:
- Python 3.13+ modern features (pattern matching, type hints, dataclasses)
- Home Assistant Core 2025.12.5 integration patterns
- Quality Scale compliance (Bronze → Silver → Gold → Platinum)
- Asynchronous programming requirements
- Coordinator patterns for data management
- Config flow implementation
- Test-driven development workflow
- Error handling and logging best practices

**When to Use**:
- Creating new sensors, binary sensors, or platforms
- Implementing service handlers
- Working with coordinators
- Debugging backend issues
- Improving test coverage
- Upgrading quality scale tier

### 2. [Lovelace Card Development with LIT 3.0](./lovelace-lit-dev/SKILL.md)

**Purpose**: Expert guidance for developing the `lovelace-growspace-manager-card` custom Lovelace card.

**Key Topics**:
- TypeScript 5.9+ with strict typing
- LIT 3.0 web components and reactive properties
- State management (Nanostores + LIT Context)
- Event handling and Home Assistant actions
- CSS theming and responsive design
- Unit testing with Vitest
- E2E testing with Playwright
- Performance optimization techniques

**When to Use**:
- Creating new card components
- Implementing dialogs and forms
- Managing application state
- Integrating with Home Assistant services
- Writing unit or E2E tests
- Debugging frontend issues
- Optimizing rendering performance

## How to Use Skills

1. **Read Before Starting**: When working on a task related to either project, use the `view_file` tool to read the relevant SKILL.md file first.

2. **Follow the Patterns**: Skills provide battle-tested patterns, common anti-patterns to avoid, and checklists to ensure quality.

3. **Reference During Development**: Keep skills open as reference material during implementation.

4. **Verify Compliance**: Use the checklists at the end of each skill to verify your work meets all requirements.

## Skill Philosophy

Skills are **living documents** that:
- Capture best practices specific to these projects
- Evolve as the codebase matures
- Prevent common mistakes
- Ensure consistency across features
- Speed up onboarding and development

## Quick Reference

### Backend (Python)
```bash
# View Home Assistant component skill
view_file /home/maxi/core/core/.agent/skills/ha-component-dev/SKILL.md

# Run backend tests
./venv/bin/pytest tests/ -v

# Check coverage
./venv/bin/pytest --cov=custom_components.growspace_manager tests/
```

### Frontend (TypeScript + LIT)
```bash
# View Lovelace card skill
view_file /home/maxi/core/core/.agent/skills/lovelace-lit-dev/SKILL.md

# Run unit tests
npm run test:unit

# Run E2E tests
npm run test:e2e

# Full coverage
npm run test:coverage:full
```

## Skill Maintenance

When updating skills:
1. Document new patterns discovered during development
2. Add anti-patterns that caused bugs
3. Update checklists with new requirements
4. Keep examples current with latest practices
5. Reference actual files from the codebase

---

**Note**: Skills complement existing workflows and GEMINI.md rules. Always follow user-defined rules first, then consult skills for implementation guidance.
