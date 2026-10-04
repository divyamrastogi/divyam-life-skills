---
name: mac-calendar
description: Add events to macOS Calendar via AppleScript. Use when the user asks to add, schedule, or create a calendar event/appointment/meeting. Default calendar is "divyamsuperb@gmail.com". Handles location, video call links, and description. Always verifies the correct time was saved.
---

# Mac Calendar

Add events to macOS Calendar using AppleScript. Uses `current date` + property mutation (the only reliable AppleScript method — string date parsing silently fails).

## Workflow

1. **Extract details** from the user's request: summary, date, start time, end time (default: start + 1 hour), location or video call link, description.
2. **Clarify** if the time is ambiguous (e.g. "10" → AM or PM). Default to the current year if no year given.
3. **Create the event** using the bundled script:

```bash
bash ~/clawd/skills/mac-calendar/scripts/add-event.sh \
  "divyamsuperb@gmail.com" \
  "Event Title" \
  "2026-06-21T10:20:00" \
  "2026-06-21T11:20:00" \
  "Location or video call URL" \
  "Optional description"
```

- Location and description are optional (pass empty string `""` to skip).
- If a video call link is provided (Zoom, Google Meet, Teams, etc.), use it as the location.

4. **Verify the event** — after creation, read back the start date to confirm:

```bash
osascript -e '
tell application "Calendar"
    tell calendar "divyamsuperb@gmail.com"
        set evts to (every event whose summary contains "EVENT_TITLE")
        repeat with evt in evts
            return (start date of evt) & " | " & (end date of evt)
        end repeat
    end tell
end tell
'
```

If the time doesn't match, **delete the broken event and recreate** — never leave a wrong entry.

5. **Confirm to the user** with a summary: title, date/time, location (if any).

## Important

- Always use the `add-event.sh` script — never write inline AppleScript date strings (they silently default to midnight).
- If the user specifies a different calendar, use that instead.
- Double-check the day of week and flag if it seems unusual (e.g. appointment on a Sunday).
