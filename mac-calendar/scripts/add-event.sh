#!/usr/bin/env bash
# Add an event to macOS Calendar via AppleScript
# Usage: add-event.sh <calendar> <summary> <startTimeISO> <endTimeISO> [location] [description]
#
# Time format: ISO 8601 local, e.g. "2026-06-21T10:20:00"

set -euo pipefail

CALENDAR="$1"
SUMMARY="$2"
START_ISO="$3"
END_ISO="$4"
LOCATION="${5:-}"
DESCRIPTION="${6:-}"

# Parse ISO datetime to AppleScript-friendly format (12h with AM/PM)
START_DISPLAY=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$START_ISO" "+%A, %d %B %Y at %I:%M:%S %p" 2>/dev/null)
END_DISPLAY=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$END_ISO" "+%A, %d %B %Y at %I:%M:%S %p" 2>/dev/null)

if [[ -z "$START_DISPLAY" || -z "$END_DISPLAY" ]]; then
  echo "ERROR: Invalid ISO datetime format. Expected YYYY-MM-DDTHH:MM:SS" >&2
  exit 1
fi

# Escape special characters for AppleScript strings
escape_for_applescript() {
  echo "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

SUMMARY_ESC=$(escape_for_applescript "$SUMMARY")
LOCATION_ESC=$(escape_for_applescript "$LOCATION")
DESCRIPTION_ESC=$(escape_for_applescript "$DESCRIPTION")

# Build location/description additions
LOC_PART=""
if [[ -n "$LOCATION" ]]; then
  LOC_PART=", location:\"${LOCATION_ESC}\""
fi

DESC_PART=""
if [[ -n "$DESCRIPTION" ]]; then
  DESC_PART=", description:\"${DESCRIPTION_ESC}\""
fi

osascript <<APPLESCRIPT
tell application "Calendar"
    tell calendar "${CALENDAR}"
        set startDate to date "${START_DISPLAY}"
        set endDate to date "${END_DISPLAY}"
        make new event with properties {summary:"${SUMMARY_ESC}", start date:startDate, end date:endDate${LOC_PART}${DESC_PART}}
    end tell
end tell
APPLESCRIPT
