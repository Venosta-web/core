# Vision checkup UI

Adds a Vision Checkup tab to the snapshots dialog in the Lovelace growspace manager card, surfacing the AI plant analysis results alongside the existing camera snapshots view.

## Background

The growspace manager backend already provides:

- `trigger_vision_checkup` service — manually triggers an AI vision analysis
- `growspace_manager/get_vision_history` WebSocket — returns up to 10 past `VisionCheckupResult` objects per growspace
- `VisionCheckupConfig` — stored on `EnvironmentConfig`, controls enable/disable and check timing offsets

No frontend exists for any of this yet.

## What we are building

### 1. Tab bar in snapshots dialog

The snapshots dialog gains a two-tab bar at the top:

- **Snapshots** — existing snapshot grid and "Capture Now" button, unchanged
- **Vision Checkup** — new tab described below

Tab state is local component state. The dialog title stays "Snapshots."

### 2. Vision Checkup tab layout

Three stacked areas:

**Top bar**
- "Run Checkup Now" button, right-aligned
- While running: spinner, button disabled
- On completion: latest result updates automatically

**Latest result panel**
- One-line header: severity chip (color-coded) + check type label (`Early`, `Mid`, `Late`, `Manual`) + formatted timestamp
- Full AI analysis text (scrollable if long)
- Issues detected as chips (e.g. `leaf_drooping`, `nitrogen_deficiency`)
- Numbered recommendations list
- Processed snapshot thumbnails in a horizontal strip (if `snapshot_paths` present)
- Empty state message when no checkups have run yet

Severity chip colors:

| Severity | Color  |
|----------|--------|
| `none`   | gray   |
| `low`    | green  |
| `medium` | amber  |
| `high`   | orange |
| `critical` | red  |

**History list** (below latest result, scrollable)
- Compact rows: formatted timestamp | check type | severity chip
- Clicking a row populates the latest result panel with that entry's data
- Selected row is highlighted
- Empty state shown when no history exists

### 3. Vision checkup config in the config dialog

A new **"Vision Checkup"** section added to the environment/camera area of the config dialog.

Fields:

| Field | Type | Default | Backend key |
|-------|------|---------|-------------|
| Enable vision checkups | toggle | `false` | `enabled` |
| Early check offset (minutes after lights on) | number | `60` | `early_check_offset_minutes` |
| Mid check (hours into light cycle) | number | `6` | `mid_check_hours` |
| Late check offset (minutes before lights off) | number | `60` | `late_check_offset_minutes` |

The section is non-interactive when no camera entities are configured on the growspace. An inline info message reads: "Configure camera entities first to enable vision checkups."

Saving calls a new WebSocket command `growspace_manager/update_vision_checkup_config` with the growspace ID and updated config fields.

## New files

```
src/services/api/vision-api.ts          # VisionAPI class (getVisionHistory, triggerVisionCheckup)
src/tests/vision-api.test.ts            # Unit tests for VisionAPI
src/tests/snapshots-dialog.test.ts      # Extended / new tests for the dialog
src/tests/config-dialog.test.ts         # Extended tests for the vision config section
```

## Modified files

```
src/dialogs/snapshots-dialog.ts         # Add tab bar + Vision Checkup tab
src/dialogs/config-dialog.ts            # Add Vision Checkup section
src/lib/constants.ts                    # Add WS_TYPE_GET_VISION_HISTORY,
                                        #     WS_TYPE_TRIGGER_VISION_CHECKUP,
                                        #     WS_TYPE_UPDATE_VISION_CHECKUP_CONFIG
src/services/api/                       # Register VisionAPI in data service
```

## Backend WebSocket command needed

`growspace_manager/update_vision_checkup_config` — saves `VisionCheckupConfig` fields for a growspace. This needs to be added to `websocket.py` and `service_registration.py` in the backend.

## Vitest coverage

### `vision-api.test.ts`
- `getVisionHistory()` sends correct WebSocket message and parses response
- `triggerVisionCheckup()` sends correct service call payload
- Both handle null and error responses gracefully

### `snapshots-dialog.test.ts`
- Tab switching renders the correct content area
- Vision tab shows loading state while fetching history
- Latest result panel renders severity chip, analysis text, issues, and recommendations
- Clicking a history row updates the result panel
- "Run Checkup Now" calls the API and refreshes results on completion
- Empty state shown when no history exists
- Error state shown when API call fails

### `config-dialog.test.ts`
- Vision section renders as disabled when no cameras are configured
- Info message shown when cameras are missing
- Fields render with correct defaults from `VisionCheckupConfig`
- Saving emits the correct `update_vision_checkup_config` WebSocket payload
