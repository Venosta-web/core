---
description: Code review workflow for Home Assistant 2025.12.5 custom component (Python 3.13) and Lovelace card (TypeScript + LIT 3.0 + Nanostore)
---

# Code Review Workflow

This workflow guides comprehensive code review for the **Growspace Manager** integration and its matching Lovelace card.

## Prerequisites

- Home Assistant 2025.12.5+ development environment
- Python 3.13+ with virtual environment activated
- Node.js 20+ for frontend tooling
- Backend: `/home/maxi/core/core/vendor/growspace_manager`
- Frontend: `/home/maxi/core/core/vendor/lovelace-growspace-manager-card`

---

## Phase 1: Backend Review (Python Custom Component)

### 1.1 Static Analysis

```bash
# Navigate to backend
cd /home/maxi/core/core/vendor/growspace_manager

# Run Ruff linting
ruff check custom_components/growspace_manager/ --fix

# Run Ruff formatting
ruff format custom_components/growspace_manager/

# Type checking with mypy
mypy custom_components/growspace_manager/ --ignore-missing-imports
```

### 1.2 Quality Scale Compliance

Check against Home Assistant Integration Quality Scale:

```bash
# Review quality_scale.yaml for compliance status
cat custom_components/growspace_manager/quality_scale.yaml
```

Key areas to verify:
- **Bronze**: Config flow, runtime data typing, entity descriptions
- **Silver**: Device entities, diagnostics, reconfiguration
- **Gold**: Strict typing, async dependencies, dynamic entity updates

### 1.3 Test Coverage

```bash
# Run tests with coverage
/home/maxi/core/core/.venv/bin/pytest --cov=custom_components.growspace_manager --cov-report=term-missing tests/

# Target: ≥95% statement coverage for all modules
```

### 1.4 Code Structure Review

Review these critical files:
- `__init__.py` - Entry setup, service registration, WebSocket API
- `coordinator.py` - Data update coordinator, state management
- `config_flow.py` - Configuration and options flow
- `models.py` - Data models (Growspace, Plant, EnvironmentConfig)
- `sensor.py`, `binary_sensor.py` - Entity implementations

### 1.5 Backend Checklist

- [ ] All functions have type hints (return types, parameters)
- [ ] Async I/O only (no blocking calls)
- [ ] Exception handling is specific (no bare `except:`)
- [ ] Logging follows HA conventions (lazy formatting, no periods)
- [ ] Services validate input with vol schemas
- [ ] Entity unique IDs are stable and predictable
- [ ] Devices properly registered with identifiers
- [ ] Translations complete in `strings.json`

---

## Phase 2: Frontend Review (TypeScript + LIT 3.0 + Nanostore)

### 2.1 Static Analysis

```bash
# Navigate to frontend
cd /home/maxi/core/core/vendor/lovelace-growspace-manager-card

# Install dependencies if needed
npm ci

# Run ESLint
npm run lint

# Run TypeScript check
npm run check

# Run Prettier formatting
npm run format
```

### 2.2 Build Verification

```bash
# Development build
npm run build

# Production build (if available)
npm run build:prod
```

### 2.3 Test Execution

```bash
# Run unit tests
npm run test

# Run E2E tests (if configured)
npm run test:e2e
```

### 2.4 Code Structure Review

Review these critical files:
- `src/growspace-manager-card.ts` - Main card component
- `src/components/` - Reusable LIT components
- `src/stores/` - Nanostore state management
- `src/types/` - TypeScript interfaces and types
- `src/utils/` - Utility functions

### 2.5 Frontend Checklist

- [ ] All components extend `LitElement` correctly
- [ ] Reactive properties use `@property()` or `@state()` decorators
- [ ] CSS uses shadow DOM scoping (`:host`, `::slotted`)
- [ ] Nanostore atoms/maps are typed and exported cleanly
- [ ] WebSocket calls handle errors gracefully
- [ ] Localization uses Home Assistant's `localize()` pattern
- [ ] Card config editor validates user input
- [ ] Accessibility: ARIA labels, keyboard navigation
- [ ] No memory leaks (event listeners cleaned up in `disconnectedCallback`)

---

## Phase 3: Integration Review

### 3.1 API Contract

Verify frontend-backend communication:

```bash
# List WebSocket commands registered by backend
grep -r "websocket_api.async_register_command" custom_components/growspace_manager/

# Check frontend WebSocket calls match
grep -r "hass.connection.sendMessagePromise\|callWS" ../lovelace-growspace-manager-card/src/
```

### 3.2 Entity State Sync

- [ ] Frontend subscribes to correct entity state changes
- [ ] State updates trigger reactive re-renders
- [ ] Optimistic UI updates revert on failure

### 3.3 Service Calls

- [ ] Frontend service calls match backend service schemas
- [ ] Error responses are displayed to user
- [ ] Loading states shown during async operations

---

## Phase 4: Security Review

### 4.1 Backend Security

- [ ] No hardcoded secrets or API keys
- [ ] User input sanitized before use
- [ ] File operations use safe path handling (`pathlib`)
- [ ] No arbitrary code execution (eval, exec)

### 4.2 Frontend Security

- [ ] No `innerHTML` with user content (use LIT templates)
- [ ] URLs validated before navigation
- [ ] Sensitive data not logged to console

---

## Phase 5: Documentation Review

- [ ] `README.md` up to date with installation instructions
- [ ] `CHANGELOG.md` documents recent changes
- [ ] Inline code comments explain complex logic
- [ ] `strings.json` translations complete

---

## Quick Commands Reference

```bash
# Backend: Full check
cd /home/maxi/core/core/vendor/growspace_manager && \
ruff check --fix custom_components/growspace_manager/ && \
ruff format custom_components/growspace_manager/ && \
/home/maxi/core/core/.venv/bin/pytest --cov=custom_components.growspace_manager --cov-report=term-missing tests/

# Frontend: Full check
cd /home/maxi/core/core/vendor/lovelace-growspace-manager-card && \
npm run lint && npm run check && npm run test
```

---

## Review Output

After completing the review, document findings in:
- `/home/maxi/.gemini/antigravity/brain/<conversation-id>/code_review.md`

Use severity levels:
- 🔴 **Critical**: Security issues, data loss risks
- 🟠 **Major**: Bugs, broken functionality
- 🟡 **Minor**: Code style, minor improvements
- 🟢 **Suggestion**: Nice-to-have enhancements
