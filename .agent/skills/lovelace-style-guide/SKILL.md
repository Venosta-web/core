
---

# Lovelace Growspace Manager: Design System & Style Guide

This guide defines the visual language and implementation patterns for the `growspace-manager` Lovelace card. It ensures a consistent, premium, and responsive user experience across all components.

## 1. Design Principles

* **Material Design 3 (MD3)**: We strictly follow MD3 principles for elevation, state layers, and interaction states.
* **Glassmorphism**: The UI utilizes semi-transparent backgrounds with backdrop blur to feel modern and integrated.
* **Component-First**: Use abstracted Lit components (e.g., `<md3-text-input>`) over raw HTML where available.
* **Responsive**: All components must adapt liquidly from mobile (< 450px) to desktop.

## 2. Core Style Architecture

Styles are centralized in `src/styles/` and must be imported into components.

```typescript
// Component Import Pattern
import { variables } from './styles/variables';
import { sharedStyles } from './styles/shared.styles';
import { uiStyles } from './styles/ui.styles';
import { dialogStyles } from './styles/dialog.styles';

static styles: CSSResultGroup = [variables, sharedStyles, uiStyles, dialogStyles, css`...`];

```

## 3. Color System

We use CSS variables to allow for easy theming and dark mode support. See `variables.ts` for the complete list.

### Semantic Gradients

Use these for high-impact elements like cards or primary headers.

* **Primary (Growth/Health)**: `var(--primary-gradient)`
* **Secondary (Water/Air)**: `var(--secondary-gradient)`
* **Danger (Alert/Error)**: `var(--danger-gradient)`

### Plant Stages

* **Veg**: `var(--stage-veg)` (#4caf50)
* **Flower**: `var(--stage-flower)` (#ff9800)
* **Dry**: `var(--stage-dry)` (#9c27b0)
* **Cure**: `var(--stage-cure)` (#2196f3)

## 4. UI Components

### Buttons (`.md3-button`)

Use `uiStyles` and apply classes. Buttons utilize `::before` pseudo-elements for state layers (hover/focus/active).

```html
<button class="md3-button primary" @click=${this._save}>
  <svg viewBox="0 0 24 24"><path d="${mdiWater}"></path></svg>
  Water Plants
</button>

<button class="md3-button tonal">Cancel</button>

<button class="md3-button text">Close</button>

<button class="md3-button danger">Delete</button>

```

### Icons

**Do not use `<ha-icon>`.** To ensure performance and style control, we import specific paths from `@mdi/js` and render them in standard SVGs.

```typescript
import { mdiSprout } from '@mdi/js';

// Inside render:
html`
  <svg style="width:24px;height:24px;fill:currentColor;" viewBox="0 0 24 24">
    <path d="${mdiSprout}"></path>
  </svg>
`

```

### Inputs & Form Controls

Do not write raw HTML input groups. Use the abstracted Lit components to ensure consistent labeling, error handling, and styling.

```html
<md3-text-input
  label="Strain Name"
  .value=${this.strain}
  .suggestions=${this.availableStrains}
  @change=${(e) => this.strain = e.detail}
></md3-text-input>

<md3-select
  label="Growspace"
  .value=${this.growspace}
  .options=${this.optionsList} ></md3-select>

<md3-number-input
  label="Row"
  .value=${this.row}
></md3-number-input>

```

## 5. Dialogs & Layouts

Dialogs use `dialog.styles.ts`. We typically wrap the content in a generic `<ha-dialog>` but hide the default actions to implement our own "Glass" container.

### Structure

1. **Container**: `.glass-dialog-container` (Flex column)
2. **Header**: `.dialog-header` containing `.dialog-icon`, titles, and a close button.
3. **Content**: `.dialog-content-grid` (Scrollable).
* **Sections**: Use `.detail-card` to group related inputs.


4. **Actions**: `.button-group` (Bottom bar).

### Example Implementation

```typescript
render() {
  return html`
    <ha-dialog open hideActions .heading=${nothing}>
      <div class="glass-dialog-container">
        <div class="dialog-header">
          <div class="dialog-icon">
            <svg viewBox="0 0 24 24"><path d="${mdiSprout}"></path></svg>
          </div>
          <div class="dialog-title-group">
            <h2 class="dialog-title">Title</h2>
            <div class="dialog-subtitle">Subtitle</div>
          </div>
          <button class="md3-button text" @click=${this._close}>
            <svg viewBox="0 0 24 24"><path d="${mdiClose}"></path></svg>
          </button>
        </div>

        <div class="dialog-content-grid">
          <div class="detail-card">
            <h3>Identity</h3>
            <div class="row-col-grid">
               <md3-text-input ...></md3-text-input>
            </div>
          </div>
        </div>

        <div class="button-group">
          <button class="md3-button tonal" @click=${this._close}>Cancel</button>
          <button class="md3-button primary" @click=${this._save}>Save</button>
        </div>
      </div>
    </ha-dialog>
  `;
}

```

### Tab Bars

For dialogs with sub-views (e.g., Add vs Clone), use the Tab pattern.

```html
<div class="tab-bar">
  <button class="tab ${active ? 'active' : ''}" @click=${...}>
    <svg...></svg> Label
  </button>
</div>

```

## 6. Layout Utilities

### Grids

* **Content Grid**: `.dialog-content-grid` automatically handles responsive wrapping.
* **Row/Col Grid**: `.row-col-grid` forces items to sit side-by-side on desktop but wrap on mobile (useful for Row/Col number inputs).

### Spacing

Always use variables:

* `var(--spacing-xs)` (4px)
* `var(--spacing-sm)` (8px)
* `var(--spacing-md)` (16px)
* `var(--spacing-lg)` (24px)

### Mobile Standard (< 450px)

Defined in `dialog.styles.ts`:

* Dialogs become full screen (`width: 100vw`, `border-radius: 0`).
* Button groups justify to `center`.
* Input grids stack vertically.

## 7. Animations

Use MD3 motion tokens defined in `variables.ts`.

```css
:host {
  transition: all var(--md3-motion-duration-short4) var(--md3-motion-easing-standard);
}

```