# Irrigation Dialog Edit/Delete Enhancement - Design Document

**Date**: 2026-02-13
**Component**: Lovelace Growspace Manager Card - Irrigation Dialog
**Type**: Feature Enhancement
**Status**: Design Complete, Ready for Implementation

## Overview

This design enhances the irrigation/drain schedule management UX by replacing the instant-delete behavior with a full edit dialog and undo-capable deletion.

### Current Behavior (Problems)

- Clicking an irrigation/drain time marker shows browser `confirm()` dialog
- Immediate deletion on confirm with no undo
- No way to edit time or duration without deleting and re-adding
- Alert-based feedback is jarring and destructive

### Desired Behavior (Solution)

- Click marker opens modal edit dialog (similar to add dialog)
- Edit time and duration with Save/Cancel buttons
- Delete button in edit dialog
- Toast notification with undo button (10s timeout)
- Optimistic UI updates with rollback on errors

## User Flow

```
1. User clicks existing irrigation/drain time marker
   ↓
2. Edit dialog opens showing current time & duration
   ↓
3. User can either:
   a) Modify time/duration and click "Save Changes"
      → Backend: remove old time, add new time (atomic operation)
      → UI: optimistic update, close dialog
   b) Click "Delete" button
      → Show toast with "Deleted [time]" and "Undo" button (5-10s timeout)
      → Backend: remove time immediately
      → UI: optimistic removal from list
      → If undo clicked: re-add the time via backend
   c) Click "Cancel"
      → Close dialog, no changes
```

## Technical Design

### Backend Constraints

- **No update service**: Backend only has `add_irrigation_time` and `remove_irrigation_time`
- **Edit Strategy**: Remove old time → Add new time (transaction with rollback)
- **Undo Strategy**: Delete immediately → Re-add on undo (within toast timeout)

### State Management

**New State Variables** (`irrigation-dialog.ts`):

```typescript
// Editing state - tracks which time is being edited
@state() private _editingIrrigationTime: {
  originalTime: string;  // Original time for backend removal
  time: string;          // Current time value (editable)
  duration: number;      // Current duration (editable)
} | undefined;

@state() private _editingDrainTime: {
  originalTime: string;
  time: string;
  duration: number;
} | undefined;

// Undo state - for toast undo functionality
@state() private _pendingUndo: {
  type: 'irrigation' | 'drain';
  time: string;
  duration: number;
  timeoutId: number;  // setTimeout ID to clear on undo
} | undefined;

// Error toast state
@state() private _errorToast: string | undefined;
```

**Why `originalTime` is needed**: When user edits the time field (e.g., from "08:00" to "09:00"), we need to remember the original "08:00" to send to `removeIrrigationTime` before adding "09:00".

### Core Methods

#### 1. Starting Edit Mode

```typescript
private _startEditingIrrigationTime(timeStr: string, duration: number) {
  this._editingIrrigationTime = {
    originalTime: timeStr,
    time: timeStr.substring(0, 5), // HH:MM format for input
    duration: duration,
  };
}

private _startEditingDrainTime(timeStr: string, duration: number) {
  this._editingDrainTime = {
    originalTime: timeStr,
    time: timeStr.substring(0, 5),
    duration: duration,
  };
}
```

#### 2. Saving Edited Time (with Transaction & Rollback)

```typescript
private async _saveEditedIrrigationTime() {
  if (!this._editingIrrigationTime || !this.device?.deviceId || !this._dataService) {
    return;
  }

  const { originalTime, time, duration } = this._editingIrrigationTime;
  const formattedNewTime = time.includes(':') && time.split(':').length === 2
    ? `${time}:00`
    : time;

  // Check for duplicate time (only if time changed)
  if (originalTime !== formattedNewTime) {
    const isDuplicate = this._irrigationTimes.some(t => t.time === formattedNewTime);
    if (isDuplicate) {
      this._showErrorToast(`Irrigation time ${time} already exists`);
      return;
    }
  }

  try {
    // Step 1: Remove old time
    await this._dataService.removeIrrigationTime({
      growspaceId: this.device.deviceId,
      time: originalTime,
    });

    try {
      // Step 2: Add new time
      await this._dataService.addIrrigationTime({
        growspaceId: this.device.deviceId,
        time: formattedNewTime,
        duration: duration,
      });

      // Success - update UI
      this._irrigationTimes = this._irrigationTimes
        .filter(t => t.time !== originalTime)
        .concat([{ time: formattedNewTime, duration }])
        .sort((a, b) => (a.time || '').localeCompare(b.time || ''));

      this._editingIrrigationTime = undefined;
      this._notifyDataChanged();

    } catch (addError) {
      // Rollback: Re-add the original time
      console.error('Failed to add new time, rolling back:', addError);
      try {
        await this._dataService.addIrrigationTime({
          growspaceId: this.device.deviceId,
          time: originalTime,
          duration: this._editingIrrigationTime.duration,
        });
        this._showErrorToast('Failed to save changes. Original time restored.');
      } catch (rollbackError) {
        console.error('Rollback failed:', rollbackError);
        this._showErrorToast('Failed to save changes. Please refresh and try again.');
      }
    }
  } catch (removeError) {
    console.error('Failed to remove old time:', removeError);
    this._showErrorToast('Failed to save changes. Please try again.');
  }
}
```

#### 3. Delete with Toast & Undo

```typescript
private async _deleteIrrigationTimeFromEdit() {
  if (!this._editingIrrigationTime || !this.device?.deviceId || !this._dataService) {
    return;
  }

  const { originalTime, duration } = this._editingIrrigationTime;

  try {
    // Delete from backend immediately
    await this._dataService.removeIrrigationTime({
      growspaceId: this.device.deviceId,
      time: originalTime,
    });

    // Optimistic UI update
    this._irrigationTimes = this._irrigationTimes.filter(t => t.time !== originalTime);

    // Close edit dialog
    this._editingIrrigationTime = undefined;

    // Show toast with undo (10 second timeout)
    this._showUndoToast('irrigation', originalTime, duration);

    this._notifyDataChanged();
  } catch (e) {
    console.error('Failed to delete irrigation time:', e);
    this._showErrorToast('Failed to delete. Please try again.');
  }
}

private _showUndoToast(type: 'irrigation' | 'drain', time: string, duration: number) {
  // Clear any existing undo timeout
  if (this._pendingUndo?.timeoutId) {
    clearTimeout(this._pendingUndo.timeoutId);
  }

  const timeoutId = window.setTimeout(() => {
    this._pendingUndo = undefined;
  }, 10000); // 10 second timeout

  this._pendingUndo = {
    type,
    time,
    duration,
    timeoutId,
  };
}

private async _undoDelete() {
  if (!this._pendingUndo || !this.device?.deviceId || !this._dataService) {
    return;
  }

  const { type, time, duration, timeoutId } = this._pendingUndo;
  clearTimeout(timeoutId);

  // Close any open edit dialogs to prevent conflicts
  this._editingIrrigationTime = undefined;
  this._editingDrainTime = undefined;

  try {
    // Re-add the deleted time
    if (type === 'irrigation') {
      await this._addIrrigationTime(time, duration);
    } else {
      await this._addDrainTime(time, duration);
    }

    this._pendingUndo = undefined;
  } catch (e) {
    console.error('Failed to undo deletion:', e);
    this._showErrorToast('Failed to undo deletion. Please try again.');
  }
}
```

#### 4. Error Toast Helper

```typescript
private _showErrorToast(message: string) {
  this._errorToast = message;
  setTimeout(() => {
    this._errorToast = undefined;
  }, 5000); // 5 second timeout
}
```

#### 5. Cleanup on Dialog Close

```typescript
private _close() {
  // Clear any pending undo operations
  if (this._pendingUndo?.timeoutId) {
    clearTimeout(this._pendingUndo.timeoutId);
    this._pendingUndo = undefined;
  }

  // Clear edit states
  this._editingIrrigationTime = undefined;
  this._editingDrainTime = undefined;

  this.dispatchEvent(new CustomEvent('close'));
}
```

### UI Rendering Changes

#### 1. Chart Marker Click Handler (Replace Confirm Dialog)

**Current** (lines 924-935):
```typescript
@click=${(e: Event) => {
  e.stopPropagation();
  if (confirm(`Remove ${type} time ${displayTime}?`)) {
    if (type === 'irrigation') {
      this._removeIrrigationTime(timeStr);
    } else {
      this._removeDrainTime(timeStr);
    }
  }
}}
```

**New**:
```typescript
@click=${(e: Event) => {
  e.stopPropagation();
  if (type === 'irrigation') {
    this._startEditingIrrigationTime(timeStr, duration);
  } else {
    this._startEditingDrainTime(timeStr, duration);
  }
}}
```

#### 2. Edit Dialog Template

Add after the add dialog template (similar structure, after line 1025):

```typescript
${editingTime
  ? html`
      <div
        class="overlay-backdrop"
        @click=${() =>
          type === 'irrigation'
            ? (this._editingIrrigationTime = undefined)
            : (this._editingDrainTime = undefined)}
      >
        <div
          class="detail-card"
          style="max-width: 400px; margin: 0; background: #2d2d2d; width: 90%;"
          @click=${(e: Event) => e.stopPropagation()}
        >
          <h3>Edit ${title} Time</h3>

          <md3-text-input
            label="Time"
            type="time"
            .value=${editingTime.time}
            @change=${(e: CustomEvent) => {
              const val = (e.target as HTMLInputElement).value || e.detail;
              if (type === 'irrigation' && this._editingIrrigationTime) {
                this._editingIrrigationTime = {
                  ...this._editingIrrigationTime,
                  time: val,
                };
              }
              if (type === 'drain' && this._editingDrainTime) {
                this._editingDrainTime = {
                  ...this._editingDrainTime,
                  time: val,
                };
              }
            }}
          ></md3-text-input>

          <md3-number-input
            label="Duration (seconds)"
            .value=${editingTime.duration}
            .min=${1}
            @change=${(e: CustomEvent) => {
              const val = parseInt(e.detail);
              if (!isNaN(val)) {
                if (type === 'irrigation' && this._editingIrrigationTime) {
                  this._editingIrrigationTime = {
                    ...this._editingIrrigationTime,
                    duration: val,
                  };
                }
                if (type === 'drain' && this._editingDrainTime) {
                  this._editingDrainTime = {
                    ...this._editingDrainTime,
                    duration: val,
                  };
                }
              }
            }}
          ></md3-number-input>

          <div class="edit-dialog-buttons">
            <button
              class="md3-button delete-button"
              @click=${() =>
                type === 'irrigation'
                  ? this._deleteIrrigationTimeFromEdit()
                  : this._deleteDrainTimeFromEdit()}
            >
              Delete
            </button>

            <div class="spacer"></div>

            <div class="action-buttons">
              <button
                class="md3-button tonal"
                @click=${() =>
                  type === 'irrigation'
                    ? (this._editingIrrigationTime = undefined)
                    : (this._editingDrainTime = undefined)}
              >
                Cancel
              </button>
              <button
                class="md3-button primary"
                @click=${() => {
                  if (type === 'irrigation') {
                    this._saveEditedIrrigationTime();
                  } else {
                    this._saveEditedDrainTime();
                  }
                }}
                style="background: ${color};"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    `
  : ''}
```

#### 3. Toast Notification Template

Add at dialog level (after button-group in main dialog):

```typescript
${this._pendingUndo
  ? html`
      <div class="toast-notification">
        <span class="toast-message">
          Deleted ${this._pendingUndo.type} time ${this._pendingUndo.time.substring(0, 5)}
        </span>
        <button class="toast-undo-button" @click=${this._undoDelete}>
          UNDO
        </button>
      </div>
    `
  : ''}

${this._errorToast
  ? html`
      <div class="toast-notification error">
        <span class="toast-message">${this._errorToast}</span>
      </div>
    `
  : ''}
```

### CSS Styles

Add to static styles (after line 366):

```css
/* Toast Notification */
.toast-notification {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(50, 50, 50, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  z-index: 10001; /* Above overlay-backdrop */
  animation: toast-slide-up 0.3s ease-out;
}

.toast-notification.error {
  background: rgba(244, 67, 54, 0.15);
  border-color: rgba(244, 67, 54, 0.3);
}

@keyframes toast-slide-up {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.toast-message {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9rem;
}

.toast-undo-button {
  background: transparent;
  border: 1px solid var(--stage-color, #2196f3);
  color: var(--stage-color, #2196f3);
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.85rem;
  text-transform: uppercase;
  transition: all 0.2s;
}

.toast-undo-button:hover {
  background: rgba(33, 150, 243, 0.1);
  border-color: var(--stage-color, #2196f3);
}

.toast-undo-button:active {
  transform: scale(0.95);
}

/* Edit Dialog - Delete Button Styling */
.md3-button.delete-button {
  background: rgba(244, 67, 54, 0.2) !important;
  color: #f44336 !important;
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.md3-button.delete-button:hover {
  background: rgba(244, 67, 54, 0.3) !important;
  border-color: rgba(244, 67, 54, 0.5);
}

/* Edit Dialog - Button Layout */
.edit-dialog-buttons {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.edit-dialog-buttons .delete-button {
  flex: 0 0 auto;
}

.edit-dialog-buttons .spacer {
  flex: 1;
}

.edit-dialog-buttons .action-buttons {
  display: flex;
  gap: 8px;
}
```

## Error Handling & Edge Cases

### Validation
- ✅ Duplicate time detection (prevents saving same time twice)
- ✅ Invalid time format handling
- ✅ Empty/null checks for device and service

### Transaction Safety
- ✅ Rollback on partial failure (add fails after remove)
- ✅ Error toast with user-friendly messages
- ✅ Console logging for debugging

### State Management
- ✅ Clear pending undo on dialog close
- ✅ Close edit dialogs on undo click (prevent conflicts)
- ✅ Only one toast visible at a time (dismiss previous)
- ✅ Debouncing for rapid clicks

### Network Errors
- ✅ Graceful degradation on API failures
- ✅ Rollback attempts with error feedback
- ✅ User can retry after error

## Testing Strategy

### Test Scenarios

**Edit Dialog Opening**:
- ✅ Click irrigation time marker → edit dialog opens with correct time/duration
- ✅ Click drain time marker → edit dialog opens with correct time/duration
- ✅ Dialog shows "Edit Irrigation Time" title (not "Add")
- ✅ Form fields pre-populated with current values

**Editing Time/Duration**:
- ✅ Change time only → saves successfully, marker moves to new position
- ✅ Change duration only → saves successfully, tooltip shows new duration
- ✅ Change both time and duration → saves successfully
- ✅ No changes made → Cancel closes dialog without backend calls
- ✅ Edit to duplicate time → shows error, doesn't save
- ✅ Edit with invalid time format → validation prevents save

**Delete from Edit Dialog**:
- ✅ Click Delete → time removed, edit dialog closes
- ✅ Toast appears with correct message "Deleted irrigation time HH:MM"
- ✅ Toast shows Undo button
- ✅ Marker disappears from timeline immediately
- ✅ Multiple deletes → each gets its own toast (previous toast dismissed)

**Undo Functionality**:
- ✅ Click Undo within 10 seconds → time restored
- ✅ Marker reappears in timeline at correct position
- ✅ Don't click Undo → toast disappears after 10 seconds
- ✅ Close dialog with pending undo → undo state cleared
- ✅ Undo after backend add succeeds → time restored correctly

**Error Scenarios**:
- ✅ Backend remove fails during edit → error toast, original time retained
- ✅ Backend add fails after remove → rollback to original time
- ✅ Network error during delete → error toast
- ✅ Network error during undo → error toast, helpful message

**Edge Cases**:
- ✅ Edit while another edit dialog open → previous dialog closes
- ✅ Start adding new time while edit open → edit closes
- ✅ Multiple rapid clicks on marker → debounced, only one dialog
- ✅ Edit irrigation while viewing drain tab → correct state maintained
- ✅ Device undefined during operation → graceful failure

### Manual Testing Checklist
```
□ Visual: Edit dialog matches add dialog styling
□ Visual: Delete button has red theme
□ Visual: Toast appears at bottom center
□ Visual: Toast slides up animation smooth
□ UX: Click outside dialog closes it
□ UX: Tab navigation works in form
□ UX: Undo button clearly visible in toast
□ UX: Timeline updates smoothly on edit
□ Performance: No lag when opening edit dialog
□ Performance: Optimistic updates feel instant
```

## Implementation Plan

### Phase 1: Core Edit Functionality
1. Add state variables for editing (`_editingIrrigationTime`, `_editingDrainTime`)
2. Implement `_startEditingIrrigationTime` and `_startEditingDrainTime`
3. Implement `_saveEditedIrrigationTime` and `_saveEditedDrainTime` (with rollback)
4. Update marker click handler (remove confirm dialog)
5. Add edit dialog template
6. Test edit flow manually

### Phase 2: Delete & Toast
7. Add undo state variable (`_pendingUndo`)
8. Implement `_deleteIrrigationTimeFromEdit` and `_deleteDrainTimeFromEdit`
9. Implement `_showUndoToast` and `_undoDelete`
10. Add toast template and CSS
11. Test delete and undo flow

### Phase 3: Polish & Error Handling
12. Add duplicate validation
13. Implement error toast system (`_errorToast`, `_showErrorToast`)
14. Add edge case handling (close dialog clears undo, etc.)
15. Add CSS animations and polish
16. Comprehensive testing (all test scenarios)
17. Update `_close()` method to clear all states

## Files to Modify

**Primary File**:
- `vendor/lovelace-growspace-manager-card/src/dialogs/irrigation-dialog.ts`
  - ~200 lines of TypeScript logic
  - ~100 lines of template rendering
  - ~80 lines of CSS
  - Total: ~380 lines (well-scoped, cohesive feature)

## Backward Compatibility

✅ **No Breaking Changes**:
- Existing add flow unchanged
- Backend API calls unchanged
- Only marker click behavior modified (user-facing improvement)
- All existing functionality preserved

## Future Enhancements

**Out of scope for this implementation**:
- [ ] **TODO**: Drag markers to change time visually (drag-and-drop on timeline)
- [ ] **TODO**: Confirm dialog for unsaved changes when closing edit dialog
- [ ] Keyboard shortcuts (ESC to close, Enter to save)
- [ ] Bulk edit multiple times
- [ ] Copy/paste irrigation schedules between days

## Success Criteria

**User Experience**:
- ✅ No accidental deletions (confirm → edit dialog)
- ✅ Can edit time/duration without re-adding
- ✅ Undo deletion within 10 seconds
- ✅ Clear visual feedback for all actions
- ✅ No loss of functionality

**Technical**:
- ✅ All existing tests pass
- ✅ No console errors
- ✅ Graceful error handling
- ✅ Optimistic UI updates
- ✅ Clean state management

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Transaction failure (remove succeeds, add fails) | Implement rollback logic to restore original time |
| Race condition with multiple edits | Clear previous edit state when starting new edit |
| Undo timeout confusion | Clear visual countdown (can be added later) |
| Network failures | Error toasts with retry suggestions |
| State leak on dialog close | Comprehensive cleanup in `_close()` method |

## Conclusion

This enhancement significantly improves the irrigation schedule management UX by:
1. Eliminating destructive one-click deletes
2. Adding full editing capability
3. Providing undo functionality
4. Maintaining backward compatibility

The implementation is well-scoped (~380 lines), follows existing patterns, and includes comprehensive error handling.
