# Irrigation Dialog - Future Enhancements (TODO)

**Related Design**: [2026-02-13-irrigation-dialog-edit-delete-enhancement-design.md](./2026-02-13-irrigation-dialog-edit-delete-enhancement-design.md)

These enhancements are **out of scope** for the initial edit/delete implementation but represent valuable future improvements to the irrigation dialog UX.

---

## TODO: Drag Markers to Change Time Visually

**Priority**: Medium
**Complexity**: High
**Dependencies**: Core edit functionality must be implemented first

### Description
Allow users to drag irrigation/drain time markers along the timeline to visually change the scheduled time, similar to dragging events in a calendar application.

### User Flow
```
1. User hovers over marker
   → Cursor changes to drag cursor (↔)
2. User clicks and drags marker horizontally
   → Marker follows cursor position
   → Timeline shows ghost position while dragging
   → Time tooltip updates in real-time
3. User releases marker at new position
   → Edit dialog opens with new time pre-filled
   → User confirms or adjusts duration
   → Save updates the schedule
```

### Technical Considerations
- **Drag Implementation**: Use Lit's `@mousedown`, `@mousemove`, `@mouseup` events
- **Snapping**: Snap to 15-minute intervals for better UX
- **Collision Detection**: Prevent dragging to overlapping times
- **Mobile Support**: Add touch event handlers for mobile devices
- **Visual Feedback**:
  - Ghost marker during drag
  - Drop zone indicators
  - Invalid drop zones (overlaps) highlighted in red

### Implementation Notes
```typescript
// Pseudo-code structure
private _isDragging = false;
private _draggedMarker: { type: 'irrigation' | 'drain', time: string } | undefined;

private _handleMarkerMouseDown(e: MouseEvent, time: string, type: string) {
  this._isDragging = true;
  this._draggedMarker = { type, time };
  // Prevent text selection during drag
  e.preventDefault();
}

private _handleTimelineMouseMove(e: MouseEvent) {
  if (!this._isDragging || !this._draggedMarker) return;

  // Calculate new time from mouse position
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const x = e.clientX - rect.left;
  const percentage = x / rect.width;
  const newTime = this._calculateTimeFromPercentage(percentage);

  // Update ghost marker position
  this._updateGhostMarker(newTime);
}

private _handleMarkerMouseUp(e: MouseEvent) {
  if (!this._isDragging) return;

  // Calculate final time
  const newTime = this._calculateDropTime(e);

  // Open edit dialog with new time
  if (this._draggedMarker.type === 'irrigation') {
    this._startEditingIrrigationTime(this._draggedMarker.time, /* duration */);
    this._editingIrrigationTime.time = newTime;
  }

  this._isDragging = false;
  this._draggedMarker = undefined;
}
```

### Testing Requirements
- ✅ Drag marker to new position → edit dialog opens with correct time
- ✅ Drag to overlapping time → shows error, prevents drop
- ✅ Drag on mobile → touch events work correctly
- ✅ Rapid clicks don't trigger drag → debouncing
- ✅ Drag outside timeline → cancels drag, reverts to original

### Estimated Effort
**~2-3 days** (includes mobile testing and polish)

---

## TODO: Confirm Dialog for Unsaved Changes

**Priority**: Low
**Complexity**: Low
**Dependencies**: Core edit functionality must be implemented first

### Description
When user makes changes in the edit dialog and tries to close it (click outside, ESC key, close button), show a confirmation dialog if there are unsaved changes.

### User Flow
```
1. User opens edit dialog and modifies time or duration
2. User clicks outside the dialog or presses ESC
   → "Unsaved changes" confirmation appears
   → Options: "Discard Changes" / "Cancel"
3a. User clicks "Discard Changes"
   → Edit dialog closes, changes lost
3b. User clicks "Cancel"
   → Returns to edit dialog, can continue editing or save
```

### Technical Considerations
- **Dirty State Tracking**: Compare current values to original values
- **Confirmation UI**: Use native browser `confirm()` or custom modal
- **Edge Cases**:
  - No changes made → close immediately (no confirmation)
  - Click save → close immediately (changes saved)
  - Delete operation → no confirmation needed (has its own undo)

### Implementation Notes
```typescript
private _hasUnsavedChanges(): boolean {
  if (!this._editingIrrigationTime) return false;

  const { originalTime, time, duration } = this._editingIrrigationTime;
  const originalData = this._irrigationTimes.find(t => t.time === originalTime);

  // Compare current values to original
  const timeChanged = time !== originalTime.substring(0, 5);
  const durationChanged = duration !== (originalData?.duration || this._irrigationDuration);

  return timeChanged || durationChanged;
}

private _handleEditDialogClose() {
  if (this._hasUnsavedChanges()) {
    const confirmed = confirm('You have unsaved changes. Discard them?');
    if (!confirmed) {
      return; // Don't close
    }
  }

  // Close dialog
  this._editingIrrigationTime = undefined;
}
```

### Alternative: Auto-Save Draft
Instead of confirmation, could auto-save draft state to localStorage and restore if dialog is reopened within a timeout. This is more complex but better UX.

### Testing Requirements
- ✅ No changes made → closes immediately
- ✅ Changes made + click outside → shows confirmation
- ✅ Changes made + press ESC → shows confirmation
- ✅ Discard changes → closes dialog, reverts state
- ✅ Cancel confirmation → returns to edit dialog
- ✅ Save then close → no confirmation (changes saved)

### Estimated Effort
**~4-6 hours** (simple confirmation) or **~1-2 days** (auto-save draft approach)

---

## Other Future Enhancements (Not Prioritized)

### Keyboard Shortcuts
- **ESC**: Close dialog (with unsaved changes check)
- **Enter**: Save changes (when focused in form)
- **Ctrl+Z**: Undo delete (even after toast disappears?)
- **Tab/Shift+Tab**: Navigate form fields

### Bulk Operations
- Select multiple irrigation times (checkboxes)
- Bulk delete selected times
- Bulk adjust duration for selected times
- Copy/paste schedule patterns

### Visual Enhancements
- Countdown timer on undo toast (visual progress bar)
- Color-coded markers based on duration (short/medium/long)
- Animate marker movement when time changes
- Show current time indicator on timeline

### Export/Import
- Export schedule to JSON/CSV
- Import schedule from file
- Copy schedule to clipboard (formatted)
- Template schedules (daily, weekly patterns)

---

## Implementation Priority

**Recommended Order**:
1. ✅ Core edit/delete functionality (current plan)
2. **Confirm dialog for unsaved changes** (quick win, prevents data loss)
3. **Drag markers** (high UX value but complex)
4. Keyboard shortcuts (if user requests)
5. Other enhancements as needed

---

**Notes**:
- These TODOs should be tracked as separate issues/tasks
- Each enhancement should have its own design review before implementation
- User feedback from initial edit/delete feature will inform priority
