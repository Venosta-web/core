---
name: Lovelace Screenshot Automation
description: Guidelines and patterns for automated screenshot capture of the Growspace Manager Lovelace card
---

# Lovelace Screenshot Automation

This skill provides the refined selectors and interaction patterns discovered while automating screenshots for the `growspace-manager-card`. These patterns are essential for reliable E2E visual capture of complex Lit-based web components in Home Assistant.

## Global Configuration

- **Base URL**: `http://127.0.0.1:8123` (Home Assistant local instance)
- **Viewport**: 1280x800 for Desktop, 375x667 for Mobile.
- **Wait Policy**: Networkidle + 5000ms initial wait for component hydration.

## Core Component Selectors

| View | Selector / Strategy |
|------|-----------|
| **Main Card** | `growspace-manager-card` |
| **Plant Card** | `growspace-plant-card` (Filter by `hasNotText: /Empty/i` for populated plants) |
| **Menu Button** | `growspace-header-actions #menu-trigger` |
| **Dialog Container** | `ha-dialog[open]` (Inside `growspace-dialog-host`) |

## Common Interaction Patterns

### Opening Dialogs via Shadow DOM
The Home Assistant frontend makes heavy use of Shadow DOM. Use recursive search or specific selectors that pierce shadow roots.

```typescript
// Click a plant card to open overview
await page.locator('growspace-plant-card').filter({ hasNotText: /Empty/i }).first()
    .locator('.plant-card-rich')
    .dispatchEvent('click', { bubbles: true, composed: true });
```

### Navigating Tabs in Dialogs
Tabs in `plant-overview-dialog` use the `.tab-btn` class.

```typescript
// Select the Timeline tab
const timelineTab = page.locator('plant-overview-dialog ha-dialog[open]')
    .locator('.tab-btn')
    .filter({ hasText: /Timeline/i });
await timelineTab.dispatchEvent('click', { bubbles: true, composed: true });
```

### Handling Menus
The header menu uses `popover="auto"`. To open it reliably:

```typescript
// Open header menu
await card.locator('growspace-header-actions #menu-trigger')
    .dispatchEvent('click', { bubbles: true, composed: true });

// Click a menu item (e.g., Strains)
await page.locator('.menu-item:visible')
    .filter({ hasText: /^Strains$/ })
    .first()
    .dispatchEvent('click', { bubbles: true, composed: true });
```

## Screenshot Strategies

1. **Wait for Loading**: Always wait for specific indicators (e.g., `md3-select` or specific chart elements) to ensure the UI is fully rendered.
2. **Crop to Dialog**: For dialog screenshots, use the bounding box of the active `ha-dialog`.
3. **Mobile View**: Force viewport size and wait for media-query-based layout shifts.

## Known Challenges
- **Strict Mode**: Many components (like `ha-dialog`) may have multiple instances in the DOM (one active, one hidden). Always filter by `:visible` or `[open]`.
- **Interception**: Use `dispatchEvent('click', ...)` instead of `.click()` to avoid click interception from transparent overlays or parent drag handlers.
