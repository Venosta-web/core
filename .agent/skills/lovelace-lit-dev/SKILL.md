---
name: Lovelace Card Development with LIT 3.0
description: Expert TypeScript + LIT 3.0 development workflow for Home Assistant custom Lovelace cards with comprehensive testing
---

# Lovelace Card Development with LIT 3.0

## Overview

This skill provides comprehensive guidance for developing high-quality Home Assistant custom Lovelace cards using **TypeScript** and **LIT 3.0**. It covers modern web component patterns, state management, testing strategies (unit + E2E), and Home Assistant integration best practices.

## Target Project

- **Card**: `lovelace-growspace-manager-card`
- **Location**: `/home/maxi/core/core/vendor/lovelace-growspace-manager-card`
- **Framework**: LIT 3.0
- **Language**: TypeScript 5.9+
- **State Management**: Nanostores + LIT Context
- **Testing**: Vitest (unit) + Playwright (E2E)
- **Build**: Rollup

## Core Principles

### 1. Modern TypeScript Standards

**Required Features**:
- ✅ Strict type checking (`strict: true`)
- ✅ Explicit types for all public APIs
- ✅ No `any` types (use `unknown` if needed)
- ✅ Const assertions and type narrowing
- ✅ Template literal types where applicable
- ✅ Discriminated unions for state variants

**Type Safety**:
```typescript
// Good - explicit types
interface PlantData {
  entity_id: string;
  name: string;
  stage: GrowthStage;
  day: number;
}

type GrowthStage = 'seedling' | 'vegetative' | 'flower' | 'dry' | 'cure';

// Better - discriminated unions for complex state
type ViewState =
  | { type: 'loading' }
  | { type: 'error'; message: string }
  | { type: 'success'; data: PlantData[] };
```

### 2. LIT 3.0 Best Practices

**Component Structure**:
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { classMap } from 'lit/directives/class-map.js';

@customElement('growspace-card')
export class GrowspaceCard extends LitElement {
  // Public properties (from config)
  @property({ type: Object }) config!: CardConfig;
  @property({ attribute: false }) hass!: HomeAssistant;
  
  // Internal state
  @state() private _selectedPlant?: string;
  @state() private _isLoading = false;
  
  static styles = css`
    :host {
      display: block;
      padding: 16px;
    }
  `;
  
  render() {
    return html`
      <div class=${classMap({ loading: this._isLoading })}>
        ${this._renderContent()}
      </div>
    `;
  }
  
  private _renderContent() {
    if (!this.hass) return html``;
    // ... render logic
  }
}
```

**Key Patterns**:
- ✅ Use `@property({ attribute: false })` for `hass` (doesn't serialize)
- ✅ Use `@state()` for private reactive state
- ✅ Prefix private methods with `_`
- ✅ Use `!` for properties that are guaranteed to be set
- ✅ Use directives (`classMap`, `styleMap`, `ifDefined`) for dynamic content

### 3. State Management

**Nanostores for Global State**:
```typescript
// stores/data-store.ts
import { atom, map } from 'nanostores';

export const $selectedGrowspace = atom<string | null>(null);

export const $growspaceData = map<Record<string, GrowspaceData>>({});

// Update
$selectedGrowspace.set('tent_1');
$growspaceData.setKey('tent_1', newData);

// Subscribe in component
import { StoreController } from '@nanostores/lit';

class MyCard extends LitElement {
  private _selectedStore = new StoreController(this, $selectedGrowspace);
  
  render() {
    const selected = this._selectedStore.value;
    return html`<div>Selected: ${selected}</div>`;
  }
}
```

**LIT Context for Hierarchical Data**:
```typescript
// contexts/hass-context.ts
import { createContext } from '@lit/context';
import type { HomeAssistant } from 'custom-card-helpers';

export const hassContext = createContext<HomeAssistant>('hass');

// Provider (top-level card)
import { provide } from '@lit/context';

@customElement('parent-card')
class ParentCard extends LitElement {
  @provide({ context: hassContext })
  @property({ attribute: false })
  hass!: HomeAssistant;
}

// Consumer (child component)
import { consume } from '@lit/context';

@customElement('child-component')
class ChildComponent extends LitElement {
  @consume({ context: hassContext })
  hass!: HomeAssistant;
}
```

### 4. Event Handling & Actions

**Custom Events**:
```typescript
// Dispatch custom events for communication
private _handlePlantClick(plantId: string) {
  this.dispatchEvent(new CustomEvent('plant-selected', {
    detail: { plantId },
    bubbles: true,
    composed: true, // Cross shadow DOM boundaries
  }));
}

// Listen for events
connectedCallback() {
  super.connectedCallback();
  this.addEventListener('plant-selected', this._handlePlantSelection);
}

disconnectedCallback() {
  super.disconnectedCallback();
  this.removeEventListener('plant-selected', this._handlePlantSelection);
}
```

**Home Assistant Actions**:
```typescript
import { handleAction } from 'custom-card-helpers';

private _handleAction(ev: Event) {
  const config = {
    tap_action: {
      action: 'call-service',
      service: 'growspace_manager.water_plant',
      data: {
        plant_id: this._selectedPlant,
      },
    },
  };
  
  handleAction(this, this.hass, config, 'tap');
}
```

### 5. Styling Best Practices

**CSS Variables for Theming**:
```typescript
static styles = css`
  :host {
    /* Use HA theme variables */
    --card-background: var(--ha-card-background, var(--card-background-color));
    --primary-text: var(--primary-text-color);
    --secondary-text: var(--secondary-text-color);
    --divider-color: var(--divider-color);
  }
  
  .card {
    background: var(--card-background);
    border-radius: var(--ha-card-border-radius, 8px);
    box-shadow: var(--ha-card-box-shadow);
    padding: 16px;
  }
  
  .header {
    color: var(--primary-text);
    font-size: 1.2rem;
    font-weight: 500;
  }
`;
```

**Responsive Design**:
```typescript
static styles = css`
  :host {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  }
  
  @media (max-width: 768px) {
    :host {
      grid-template-columns: 1fr;
    }
  }
`;
```

### 6. Testing Strategy

**Unit Tests (Vitest)**:
```typescript
// tests/unit/my-component.spec.ts
import { fixture, html, expect } from '@open-wc/testing-helpers';
import '../../src/components/my-component';
import type { MyComponent } from '../../src/components/my-component';

describe('MyComponent', () => {
  let element: MyComponent;
  
  beforeEach(async () => {
    element = await fixture<MyComponent>(html`
      <my-component .hass=${createMockHass()}></my-component>
    `);
  });
  
  it('renders correctly', () => {
    expect(element).to.exist;
    expect(element.shadowRoot?.querySelector('.container')).to.exist;
  });
  
  it('handles user interaction', async () => {
    const button = element.shadowRoot?.querySelector('button');
    button?.click();
    await element.updateComplete;
    
    expect(element.selectedItem).to.equal('expected-value');
  });
});
```

**E2E Tests (Playwright)**:
```typescript
// tests/e2e/plant-management.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Plant Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8123');
    await page.fill('input[name="username"]', 'test');
    await page.fill('input[name="password"]', 'test');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/lovelace/**');
  });
  
  test('should add new plant successfully', async ({ page }) => {
    // Navigate to growspace card
    await page.click('text=Growspace Manager');
    
    // Open add plant dialog
    await page.click('[data-action="add-plant"]');
    
    // Fill in plant details
    await page.fill('input[name="plant_name"]', 'Test Plant');
    await page.selectOption('select[name="strain"]', 'Blue Dream');
    
    // Submit
    await page.click('button:has-text("Add Plant")');
    
    // Verify plant appears in list
    await expect(page.locator('text=Test Plant')).toBeVisible();
  });
});
```

**Run Tests**:
```bash
# Unit tests
npm run test:unit

# Unit tests with watch mode
npm run test:unit:watch

# Unit tests with coverage
npm run test:coverage

# E2E tests
npm run test:e2e

# E2E tests with coverage
npm run test:e2e:coverage

# Full coverage report
npm run test:coverage:full
```

### 7. Build & Development Workflow

**Development Build**:
```bash
# Build card
npm run build

# Build with coverage instrumentation
npm run build:coverage

# Watch mode (requires separate file watcher setup)
# Home Assistant will hot-reload on file changes
```

**File Structure**:
```
src/
├── components/           # LIT components
│   ├── growspace-card.ts
│   ├── plant-card.ts
│   └── dialogs/
│       ├── plant-dialog.ts
│       └── settings-dialog.ts
├── stores/              # Nanostores
│   ├── data-store.ts
│   └── ui-store.ts
├── contexts/            # LIT contexts
│   └── hass-context.ts
├── types/               # TypeScript types
│   ├── card-config.ts
│   └── hass.ts
├── utils/               # Utilities
│   ├── formatters.ts
│   └── validators.ts
└── index.ts            # Entry point
```

### 8. Home Assistant Integration

**Card Configuration**:
```typescript
interface CardConfig {
  type: string;
  entity?: string;
  name?: string;
  show_header?: boolean;
  tap_action?: ActionConfig;
  hold_action?: ActionConfig;
  double_tap_action?: ActionConfig;
}

export class GrowspaceCard extends LitElement {
  @property({ type: Object }) config!: CardConfig;
  
  setConfig(config: CardConfig) {
    if (!config) {
      throw new Error('Invalid configuration');
    }
    this.config = config;
  }
  
  // Required for card to appear in card picker
  static getConfigElement() {
    return document.createElement('growspace-card-editor');
  }
  
  static getStubConfig() {
    return {
      type: 'custom:growspace-manager-card',
      show_header: true,
    };
  }
}
```

**Card Editor**:
```typescript
@customElement('growspace-card-editor')
export class GrowspaceCardEditor extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) config!: CardConfig;
  
  private _configChanged(ev: Event) {
    const target = ev.target as HTMLInputElement;
    const newConfig = {
      ...this.config,
      [target.name]: target.checked ?? target.value,
    };
    
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config: newConfig },
      bubbles: true,
      composed: true,
    }));
  }
  
  render() {
    return html`
      <ha-switch
        name="show_header"
        .checked=${this.config.show_header}
        @change=${this._configChanged}
      >
        Show Header
      </ha-switch>
    `;
  }
}
```

### 9. Performance Optimization

**Efficient Rendering**:
```typescript
import { cache } from 'lit/directives/cache.js';
import { repeat } from 'lit/directives/repeat.js';

render() {
  return html`
    ${cache(this._isLoading ? this._renderLoader() : this._renderContent())}
  `;
}

private _renderPlants() {
  return html`
    ${repeat(
      this._plants,
      (plant) => plant.entity_id, // Key function
      (plant) => this._renderPlant(plant) // Template function
    )}
  `;
}
```

**Lazy Loading**:
```typescript
private async _loadDialog() {
  if (!this._dialogElement) {
    await import('./dialogs/plant-dialog');
    this._dialogElement = document.createElement('plant-dialog');
  }
  return this._dialogElement;
}
```

### 10. Common Patterns

**Data Fetching**:
```typescript
private async _fetchGrowspaceData() {
  if (!this.hass) return;
  
  try {
    const result = await this.hass.callWS<GrowspaceData>({
      type: 'growspace_manager/get_data',
      growspace_id: this.config.growspace_id,
    });
    
    $growspaceData.setKey(this.config.growspace_id, result);
  } catch (err) {
    console.error('Failed to fetch growspace data:', err);
    this._showError('Failed to load data');
  }
}
```

**Dialogs**:
```typescript
private async _openPlantDialog(plantId: string) {
  const dialog = await this._loadDialog();
  dialog.hass = this.hass;
  dialog.plantId = plantId;
  
  dialog.addEventListener('closed', () => {
    this._refreshData();
  }, { once: true });
  
  await dialog.show();
}
```

**Service Calls**:
```typescript
private async _waterPlant(plantId: string, amount: number) {
  try {
    await this.hass.callService(
      'growspace_manager',
      'water_plant',
      {
        plant_id: plantId,
        amount_ml: amount,
      }
    );
    
    this._showSuccess('Plant watered successfully');
    await this._refreshData();
  } catch (err) {
    console.error('Failed to water plant:', err);
    this._showError('Failed to water plant');
  }
}
```

## Anti-Patterns to Avoid

❌ **Using `any` Type**
```typescript
private _data: any;  // ❌ Never use any
private _data: unknown;  // ✅ Use unknown if type is truly unknown
private _data: GrowspaceData;  // ✅✅ Best - use specific type
```

❌ **Not Cleaning Up Event Listeners**
```typescript
connectedCallback() {
  super.connectedCallback();
  window.addEventListener('resize', this._handleResize);
  // ❌ Missing cleanup in disconnectedCallback
}
```

❌ **Mutating Props**
```typescript
@property({ type: Object }) config!: CardConfig;

someMethod() {
  this.config.name = 'new name';  // ❌ Don't mutate props
  this.config = { ...this.config, name: 'new name' };  // ✅ Create new object
}
```

❌ **Synchronous Heavy Operations in Render**
```typescript
render() {
  // ❌ Heavy computation in render
  const processedData = this._heavyComputation(this.data);
  return html`...`;
}

// ✅ Use @state and compute in updated()
@state() private _processedData: ProcessedData[] = [];

updated(changedProps: PropertyValues) {
  if (changedProps.has('data')) {
    this._processedData = this._heavyComputation(this.data);
  }
}
```

❌ **Not Waiting for updateComplete**
```typescript
async test() {
  element.value = 'new value';
  expect(element.textContent).to.equal('new value');  // ❌ May fail
  
  await element.updateComplete;  // ✅ Wait for update
  expect(element.textContent).to.equal('new value');
}
```

## Development Checklist

Before marking work complete:

- [ ] TypeScript compiles without errors
- [ ] All unit tests pass (`npm run test:unit`)
- [ ] E2E tests pass (`npm run test:e2e`)
- [ ] No console errors in browser
- [ ] Responsive design works on mobile
- [ ] Dark mode styling tested
- [ ] All public APIs have type definitions
- [ ] Components use proper LIT decorators
- [ ] Event listeners are cleaned up
- [ ] Code is formatted (`npm run format`)
- [ ] Linting passes (`npm run lint`)

## Quick Commands Reference

```bash
# Development
npm run build                  # Build production bundle
npm run build:coverage         # Build with instrumentation

# Testing
npm run test                   # Run all unit tests
npm run test:unit             # Run unit tests
npm run test:unit:watch       # Watch mode for unit tests
npm run test:coverage         # Unit tests with coverage
npm run test:e2e              # E2E tests
npm run test:e2e:coverage     # E2E with coverage
npm run test:coverage:full    # Combined coverage report

# Code Quality
npm run lint                  # Run ESLint
npm run format               # Format with Prettier
```

## Resources

- **LIT Documentation**: Use Context7 - `resolve-library-id lit`
- **Package Config**: `package.json`
- **TypeScript Config**: `tsconfig.json`
- **Rollup Config**: `rollup.config.js`
- **Tests**: `tests/unit/` and `tests/e2e/`

## Success Metrics

A well-implemented Lovelace card:

- ✅ Fast initial load (< 100ms)
- ✅ Smooth animations (60 FPS)
- ✅ Fully typed (no `any`)
- ✅ >90% test coverage
- ✅ Accessible (ARIA labels, keyboard navigation)
- ✅ Responsive across devices
- ✅ Consistent with HA design language
- ✅ Graceful error handling
- ✅ Proper loading states

---

**Remember**: Type safety prevents bugs. Test everything. Performance matters. User experience is paramount.
