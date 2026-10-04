---
name: interface-design-rules
description: "Load for ANY UI/UX work — building or reviewing web pages, components, dashboards, forms, apps, landing pages, or frontend design. Distilled design rules from interfaces.dev covering layout, motion, typography, color, accessibility, forms and microcopy. Apply proactively; never wait to be asked."
---

# Interface Design Rules (interfaces.dev cheat sheet, distilled for AI agents)

Apply these whenever generating or reviewing UI code. They are defaults, not suggestions — deviate only with a stated reason.

## Layout & Spacing
- Nested elements get **concentric border radius**: outer = inner + padding.
- Prefer **optical alignment** over geometric alignment.
- Space between groups ≥ 2× space between items in a group (e.g. 8px items, 16px+ groups).
- Keep long lines to **60–75 characters**; never wider for long-form text.
- Buttons with text + icon get slightly smaller padding on the icon side.

## Depth & Borders
- Use **layered box-shadows** for depth instead of borders.
- Give images a 1px outline offset −1px: black at 8% opacity (light), white at 8% (dark).

## Motion
- Animate from the **trigger** (transform-origin follows trigger position), not the center.
- Exit animations are **subtler than entrances**: shorter distance, fade + 4px blur.
- Frequently-opened menus: skip open animation, animate close only.
- Never `transition: all` — name exact properties.
- Buttons scale to 0.95–0.98 on press, `transition: scale 200ms ease-out`.
- Icon swaps: crossfade + new icon scales 0.25→1, blur 4px→0 (reverse for old).
- CSS transitions for interactions (reversible mid-flight); keyframes only for one-shot sequences.
- No transitions when switching light/dark mode.
- Flicker while animating? Add `will-change: transform` (especially iOS Safari).
- Entrances animate in small staggered groups, never one giant block.
- Nothing animates on page load unless intentional. Hover/frequent interactions stay instant.
- Wrap animations in `@media (prefers-reduced-motion: no-preference)`.

## Typography
- Web fonts: **.woff2 only** (.woff fallback; never .ttf/.otf).
- `font-variant-numeric: tabular-nums` on timers, counters, prices, tables (skip if monospace).
- `text-wrap: balance` on headings, `text-wrap: pretty` on descriptions (neither on long-form text).
- Contain long words/IDs with `overflow-wrap: break-word`; `white-space: nowrap` on badges/labels.
- Root layout: `-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale`.
- Normal capitalization in source text; use `text-transform` for display changes.
- Smart punctuation: curly quotes, en dash (–) for ranges, em dash (—) for asides, … not ...
- Underlines must not cross letter tails: `text-underline-position: from-font; text-decoration-skip-ink: auto`.
- Truncated text (ellipsis) must be readable via tooltip or expanded view.

## Color & Theming
- Every palette step has a purpose (page bg, hover, border, solid fill, body text). No orphan steps.
- Components use **semantic tokens** (`--color-text-secondary`), never primitives (`--blue-500`).
- Token names describe **purpose**: `--color-accent-solid`, not `--color-blue-button`.
- Reserve "accent" for brand; "primary" never means both brand and body text.
- Measure contrast against the **immediately adjacent** background.
- Dark mode gets its own palette — never invert the light one.
- One theme-switch mechanism only: `prefers-color-scheme` XOR `.dark` class.
- Gradient blending: `oklab` = even brightness, `oklch` = vivid midtones, `srgb` = muted.

## Accessibility
- Native elements first: `<button>` for buttons, `<a>` for links.
- Style `:focus-visible`; never remove outlines without a replacement.
- Only `tabindex="0"` and `tabindex="-1"` — never positive values.
- Icon-only buttons get descriptive `aria-label`; never `aria-hidden` on focusable elements.
- Alt text explains purpose + content; decorative images get `alt=""`.
- Every input has a visible `<label>`; set `type` and `inputmode` to match content.
- **Never block paste** (passwords, OTPs).
- Submit stays enabled until the request starts; validate on submit; `aria-invalid="true"` + `aria-describedby` on errors; focus the first invalid field.
- Hit areas ≥24×24px; aim 44×44 touch / 40×40 desktop; never overlapping.
- `pointer-events: none` on decorative glows/gradients.
- Hover styles inside `@media (hover: hover)` (touch :hover sticks after tap).
- `role="status"` for routine updates; `role="alert"` only for urgent errors.
- Never color alone for status — add icon/label/underline.
- Skip-to-content link is the first Tab stop; `scroll-margin-top` on linked headings.

## Forms & Microcopy
- Button labels start with a verb: "Save draft", "Delete project" — never "OK!" or bare "Yes".
- Confirmation buttons say what happens: "Delete project" beside "Cancel".
- One forward label per flow: "Continue" (or "Next") everywhere.
- Links describe their destination — not "click here".
- Consistent capitalization everywhere; sentence case is the default.
- Toggles describe the ON state: "Send read receipts", not "Disable read receipts".
- Empty states explain what belongs there + give one action — never blank.
- Address the reader as "you", not "the user".

Source: https://interfaces.dev/cheat-sheet
