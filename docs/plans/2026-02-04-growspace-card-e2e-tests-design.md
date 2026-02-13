# E2E Testing Design for Growspace Manager Lovelace Card

**Date:** 2026-02-04
**Status:** Design Approved
**Target:** Playwright E2E tests for user interactions and data flow

## Overview

This design establishes end-to-end testing for the Growspace Manager Lovelace card using Playwright. The tests verify user interactions work correctly and the card stays synchronized with backend data changes.

## Goals

Test these critical areas:
- **Plant management** - Adding, editing, moving, and removing plants
- **Environmental monitoring** - Stress indicators, mold warnings, sensor data updates
- **Configuration dialogs** - Settings changes, validation, persistence

Verify **full round-trip data flow**:
1. User interaction triggers UI action
2. Backend service processes the change
3. WebSocket event emits state update
4. Card re-renders with new data
5. UI displays correct state

## Architecture

### Three-Layer Design

**1. Test Orchestration (Playwright)**
- Each test file covers one feature area
- Page Object Model encapsulates card selectors and interactions
- Custom fixtures manage HA setup and teardown per test

**2. Backend Layer (Home Assistant)**
- Each test creates an isolated config entry
- Tests call HA services via REST API or WebSocket
- Coordinator processes changes and emits state updates

**3. Verification Layer**
- Wait for WebSocket events after backend changes
- Verify DOM updates using Playwright auto-waiting
- Assert on visible UI elements
- Screenshot comparison for visual regression

### Example Flow

```
User clicks "Add Plant"
→ Form appears
→ Test fills form
→ Calls growspace_manager.add_plant service
→ Backend processes request
→ WebSocket emits state change
→ Card re-renders
→ Test verifies plant appears in grid
```

## Directory Structure

```
tests/e2e/
├── fixtures/
│   ├── ha_setup.ts          # Config entry setup/teardown
│   ├── authentication.ts     # Token management
│   └── growspace_fixtures.ts # Seed data helpers
├── pages/
│   ├── GrowspaceCard.ts      # Page Object for card
│   └── Dialogs.ts            # Reusable dialog interactions
├── specs/
│   ├── plant-management.spec.ts
│   ├── environmental-monitoring.spec.ts
│   └── configuration.spec.ts
└── playwright.config.ts
```

## Key Components

### GrowspaceCard Page Object

Encapsulates all card interactions:

```typescript
class GrowspaceCard {
  // Selectors use data attributes for reliability
  private plantCard = (plantId: string) =>
    this.grid.locator(`[data-plant-id="${plantId}"]`);

  // High-level interaction methods
  async addPlant(position, plantData) {
    await this.addPlantButton.click();
    await this.fillPlantForm(plantData);
    await this.waitForStateUpdate();
    await expect(this.plantCard(plantData.name)).toBeVisible();
  }

  async movePlant(plantId, newPosition) { }
  async getPlantCard(plantId) { }
  async getStressIndicators() { }
  async waitForCoordinatorUpdate() { }
}
```

### HA Setup Fixture

Manages backend state:

```typescript
async function haFixture({ page }) {
  const entryId = await createConfigEntry();

  const callService = async (domain, service, data) => {
    await page.evaluate(({ domain, service, data }) => {
      return window.hass.callService(domain, service, data);
    }, { domain, service, data });
  };

  await test.afterEach(async () => {
    await deleteConfigEntry(entryId);
  });

  return { entryId, callService };
}
```

### Authentication Strategy

Use long-lived access tokens:

1. Generate token manually (one-time setup)
2. Store in `.env.test`: `HA_ACCESS_TOKEN=xxx`
3. Inject token into Playwright context headers
4. Skip login UI entirely

```typescript
const context = await browser.newContext({
  baseURL: 'http://localhost:8123',
  extraHTTPHeaders: {
    'Authorization': `Bearer ${process.env.HA_ACCESS_TOKEN}`
  }
});
```

## Round-Trip Testing Pattern

Each interaction follows this verified flow:

**1. User Action (Playwright)**
```typescript
await growspaceCard.addPlant({ x: 0, y: 0 }, {
  name: "Test Plant",
  strain: "Blue Dream",
  stage: "vegetative"
});
```

**2. Service Call (via HA API)**
```typescript
await haFixture.callService('growspace_manager', 'add_plant', {
  config_entry_id: entryId,
  position: { x: 0, y: 0 },
  name: "Test Plant"
});
```

**3. Backend Processing**
- Coordinator receives service call
- Updates internal state
- Persists to HA registry
- Emits state change via WebSocket

**4. WebSocket Event Handling**
```typescript
await growspaceCard.waitForStateUpdate('sensor.growspace_plants');
```

**5. UI Verification**
```typescript
const plant = await growspaceCard.getPlantCard('test_plant');
await expect(plant).toBeVisible();
await expect(plant).toContainText('Test Plant');
await expect(plant).toHaveAttribute('data-stage', 'vegetative');
```

## Error Handling

### WebSocket Timing
- Use Playwright's `waitForSelector` with 5-10s timeouts
- Implement `waitForCoordinatorUpdate()` that polls for state changes
- Retry flaky WebSocket connections: 3 attempts with exponential backoff

### Service Call Failures
```typescript
try {
  await haFixture.callService('growspace_manager', 'add_plant', data);
} catch (error) {
  console.error('Service call failed:', { service: 'add_plant', data, error });
  throw new Error(`Failed to add plant: ${error.message}`);
}
```

### Test Isolation
- Always run cleanup in `afterEach` hook, even on failure
- Use try-finally to ensure resource release
- Verify clean slate before each test: `expect(plants).toHaveCount(0)`

### Flakiness Mitigation
- Screenshot on failure for debugging
- Retry tests automatically (max 2 retries) for network/timing issues
- Fail fast on assertion errors (don't retry logic bugs)
- Log each service call, WebSocket event, and UI interaction

## Test Scenarios

### Plant Management (`plant-management.spec.ts`)

**Core Operations:**
- Add plant to empty grid
- Move plant to new position (drag-drop)
- Edit plant details (strain, stage, notes)
- Remove plant from grid
- Add multiple plants

**Edge Cases:**
- Prevent duplicate positions
- Handle max grid capacity
- Concurrent plant additions

### Environmental Monitoring (`environmental-monitoring.spec.ts`)

**Display Tests:**
- Show stress indicators when thresholds exceeded
- Mold risk warning displays correctly
- Optimal conditions show green status
- Sensor data updates in real-time (within 2s)

**Data Flow:**
- Coordinator update triggers UI refresh
- Multiple sensor updates batched correctly

### Configuration (`configuration.spec.ts`)

**Dialog Interaction:**
- Open settings dialog from card menu
- Navigate between config tabs
- Close dialog without saving (discard changes)
- Close with X button vs Cancel button

**Configuration Changes:**
- Update grid dimensions (verify re-render)
- Toggle display options (stress indicators on/off)
- Change update interval (verify coordinator respects it)
- Update warning thresholds (verify new limits apply)

**Validation & Persistence:**
- Validate invalid inputs (show error messages)
- Config persists after page reload
- Config changes trigger coordinator refresh
- Reset to defaults button works

## Test Execution

### Playwright Configuration

```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './tests/e2e/specs',
  timeout: 30000,
  retries: 2,
  workers: 1, // Sequential for HA isolation
  use: {
    baseURL: 'http://localhost:8123',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },
});
```

### Local Commands

```bash
# Run all E2E tests
npm run test:e2e

# Run specific suite
npm run test:e2e -- plant-management

# Debug mode (headed browser)
npm run test:e2e -- --headed --debug

# Update snapshots
npm run test:e2e -- --update-snapshots
```

### CI Integration (GitHub Actions)

**Prerequisites:**
1. Start HA test instance in container
2. Wait for HA health check
3. Generate access token
4. Run Playwright tests
5. Upload failure artifacts (screenshots, videos, traces)

**Configuration:**
- Run on PRs and main branch
- Fail PR if tests fail
- Store test results for 30 days
- Sequential execution (workers: 1) for config entry isolation

## Implementation Notes

### Selector Strategy
- Use data attributes (`data-plant-id`, `data-stress-type`) for reliable selection
- Avoid CSS classes that may change with styling
- Use semantic roles (`getByRole('button')`) where possible

### WebSocket Handling
- Implement helper to wait for specific state entity updates
- Poll `window.hass.states` for changes
- Timeout after 10 seconds with clear error message

### Config Entry Isolation
- Each test creates a fresh config entry
- No shared state between tests
- Clean up even on test failure

### Page Object Patterns
- High-level methods mirror user actions (`addPlant`, not `clickAddButton`)
- Methods encapsulate waiting and verification
- Return locators for flexible assertions

## Success Criteria

- 95%+ test coverage of user interactions
- All tests pass reliably (< 1% flakiness)
- Full round-trip verification for each action
- Clear failure messages with screenshots
- Tests run in < 5 minutes locally
- CI integration passes consistently
