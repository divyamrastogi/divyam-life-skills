---
name: generating-extension-store-assets
description: Use when a Chrome extension repo needs Chrome Web Store listing assets — screenshots, promo tile, marquee — or when asked to build/fix a screenshot generation script, store assets look empty/broken/like debug output, or a CWS listing/Featured-badge audit flags thin store assets.
---

# Generating Extension Store Assets

## Overview

Read the extension's code to find every screenshot-worthy scenario, then commit a repeatable script that installs the **real extension** in Chromium, stages honest lived-in state, captures it, and composites branded store-sized frames. The images are evidence of the product: **everything inside a device/UI frame must be genuinely rendered by the extension** — only the marketing frame around it is designed.

## Workflow

1. **Read the code first.** From manifest + source, inventory: surfaces (popup, options, onboarding page), `chrome.storage` keys actually read (grep `storage.(local|sync|session).get`), content-script behaviors and their trigger paths (keyboard handlers, DOM insertions like toasts/overlays), and the brand palette from its CSS.
2. **Plan the shot list** (max 5 screenshots, 1280×800): narrative order — core surface populated → depth/customization → each content-script behavior *in action* on an unbranded fixture page → put the strongest shot FIRST (it's the listing hero).
3. **Write `tests/screenshots.js`** (or `scripts/`): plain Node + Playwright + sharp, committed, run via an npm script. Follow the capture/composite skeleton and gotcha list in [reference.md](reference.md) — several are store-rejection or silent-failure traps.
4. **Run it, then LOOK at every PNG** you produced (read the image files). Judge each against the rubric in reference.md. Iterate until all pass — the first render never passes.
5. **Verify mechanically**: exact dimensions (1280×800 / 440×280 / 1400×560), PNG without alpha, then commit script + assets.

## Iron rules (each one failed in baseline testing)

| Shortcut | Why it's wrong |
|---|---|
| Shim/mocking `chrome.*` and loading raw HTML | Works only on toy extensions; real SW/messaging/content scripts silently break. Install for real: `launchPersistentContext` + `--load-extension`, seed storage inside the real extension page. |
| Shipping an empty state as a screenshot ("it's deliberate first-run UX") | Store screenshots sell value delivered, not first-run emptiness. Seed state so every shot is populated. |
| Fabricating browser chrome, URL bars, or OS windows around captures | Invented UI in a product listing is a fabricated record. Frame with abstract branded canvases instead. |
| Skipping the visual pass because dimensions check out | Dimension checks can't see empty cards, light/dark mismatches, or banners covering content. Look at every image. |
| Copy claiming features you didn't verify in code | Headlines must match what the code does. |

## When NOT to use

Not for generating app-store assets from mockups/designs (no extension to run), and not a substitute for listing text copywriting.
