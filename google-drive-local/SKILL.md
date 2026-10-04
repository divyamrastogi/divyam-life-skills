---
name: google-drive-local
description: "Save, organize, and manage files in Google Drive via the local macOS Drive folder. No API auth needed."
---

# google-drive-local

Save, organize, and manage files in Google Drive via the local macOS filesystem mount.

## When to Use

Whenever the user asks to:
- Save/upload/store a file to Google Drive
- Organize Google Drive folders
- Move or reorganize files in Drive
- Find a file in Drive

## Key Principle

**Never use `gog drive` API or ask for Google OAuth.** The Mac has Google Drive for Desktop installed with the local mount at:

```
~/Google Drive/My Drive/
```

All operations are plain filesystem operations (`cp`, `mv`, `mkdir`, `ls`). Google Drive desktop syncs changes to the cloud automatically.

## Base Path

```bash
DRIVE_BASE="$HOME/Google Drive/My Drive"
```

## Workflow

1. **Locate the target folder** — `ls` and `find` under `$DRIVE_BASE` to find the right location. Use `grep -i` for fuzzy matching.
2. **Create folder structure if needed** — `mkdir -p "$DRIVE_BASE/path/to/folder"`
3. **Copy/move the file** — `cp <source> "$DRIVE_BASE/path/to/folder/filename.ext"`
4. **Organize old files** — If saving a renewal/updated version, check for existing files and move them to a previous-year or `Archive` subfolder before adding the new one.
5. **Confirm** — Show the resulting folder structure with `ls -laR` (limit depth).

## Folder Organization Rules

- When saving a yearly/renewal document (insurance, tax, etc.), organize by year:
  ```
  Parent Folder/
  ├── 2023-24/
  ├── 2024-25/
  └── 2026-27/
  ```
- Ask before reorganizing existing structure (don't clobber).
- Preserve existing folders that aren't year-based (e.g., surgery records, discharge summaries).

## Common Folder Locations

Known top-level folders under `Family Documents/`:
- `Health Insurance/` — per-person subfolders (Chhaya, Deeksha, Divyam, Dhruv, Mukesh Rastogi Papa)
- `Insurances/` — other insurance types (Car, Bike, Achyut, Deeksha, Divyam)
- `Aadhaar/`, `PAN/`, `Passport/`, `Bank/`, etc.

Also at root level:
- `Mummy Insurance December 2024/` — treatment records

## Error Handling

- If `~/Google Drive/My Drive/` doesn't exist, Google Drive for Desktop may not be running. Tell the user to open the Google Drive app.
- Check the file was copied successfully with `ls -la` after copy.

## Do NOT

- ❌ Use `gog drive` or `gog auth add --services drive`
- ❌ Ask the user to authorize Google OAuth
- ❌ Mention Google API authentication at all
- ❌ Use `web_fetch` or any web upload — purely local filesystem ops
