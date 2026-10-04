# Store Assets — Rubric, Gotchas, and Script Skeleton

Distilled from building and twice repairing the Smart Video Controls asset
pipeline, plus the CWS Asset Studio design work.

## Quality rubric (judge every rendered PNG against this)

- **Populated, lived-in state.** No empty lists, zero counts, or placeholder text
  (`Note 1`, `test`, lorem). Seed plausible data mid-workflow — one item done,
  one in progress; numbers that look used (`4:23`, not `0:00` or `99:99`).
- **One coherent moment.** Paired state must agree (a "playing" icon with a
  "playing" label; a progress bar consistent with the timestamp). No
  contradictory states in one frame.
- **No anti-marketing chrome.** Hide first-run banners, privacy notices,
  "rate us" begs, debug/status lines, and log-ish text or emoji. Nothing may
  cover the feature being shown.
- **Consistent color scheme.** Headless Chromium reports `light` by default —
  emulate `prefers-color-scheme` explicitly (`colorScheme` on the context) and
  keep every shot + frame treatment consistent. Glow/gradient treatments read
  well on dark; on light use flat tint + soft shadow (glow reads as smudge).
- **Narrative order.** Establish core value → show depth/customization → prove
  behaviors in action. Strongest shot first — it is the listing hero.
- **Honest capture.** Everything inside the shot is real extension output.
  In-action shots use a **generic, unbranded fixture page** (no Netflix/YouTube
  look-alikes — store policy) served locally or via `route()` interception.

## Compliance (store-rejection traps)

- Screenshots exactly **1280×800** (or 640×400); tile **440×280**; marquee
  **1400×560**. `deviceScaleFactor` MUST be 1 — DPR 2 emits 2560×1600 and the
  Web Store rejects the upload.
- **PNG with no alpha channel** — flatten with sharp (Chromium screenshots are
  RGBA).
- **No promotional text, pricing, or claims** rendered into tile/marquee
  imagery beyond product name + plain-language tagline.
- **No real third-party domains, brands, or logos** anywhere in a shot —
  including URL text the extension itself renders (a real site name once
  shipped in a host chip and had to be scrubbed). Use `*.example.com`.

## Validating against any published extension (Web Store URL)

`scripts/fetch-extension.mjs <webstore-url-or-id> <dest-dir>` downloads the
extension's CRX3 from Google's update endpoint (no auth) and unpacks it into a
loadable directory. Caveats:

- This is the **built artifact** — possibly minified. Manifest, surfaces, and
  storage keys are still greppable; deep comprehension is harder than a repo.
- Manifest fields may be localized (`__MSG_extName__`) — resolve them from
  `_locales/<default_locale>/messages.json`.
- It is untrusted third-party code: it runs only inside the throwaway Chromium
  profile. Only use reputable extensions, and never upload assets for an
  extension you don't own.

## Technical gotchas

- Load the real extension:
  `chromium.launchPersistentContext(freshTmpDir, { headless: false, deviceScaleFactor: 1, colorScheme: 'dark'|'light', args: ['--headless=new', '--disable-extensions-except='+dir, '--load-extension='+dir] })`.
  The `--headless=new` arg is load-bearing: plain `headless: true` may select the
  chrome-headless-shell binary, which silently cannot load extensions — the
  service worker never registers and everything hangs with no error. Retry
  fully headed (drop the arg) if registration still fails.
- Chrome MUTATES the loaded extension directory: `--load-extension` can write a
  multi-MB `_metadata/generated_indexed_rulesets/` cache into it (extensions
  with declarativeNetRequest rules). Load from a copy of the source tree, or
  delete + gitignore `_metadata/` afterward.
- Surfaces that resolve "the current tab" via
  `chrome.tabs.query({active: true, currentWindow: true})` (popups opened as
  tabs, executeScript-based tools) will target THEMSELVES if the popup tab is
  frontmost. Open the content/fixture tab first, re-front it with
  `page.bringToFront()`, then drive the popup tab in the background.
- Don't guess selectors for extension-injected overlays — read the extension's
  own injection code for the real DOM shape (e.g. an overlay iframe created
  without a `src` attribute never matches `iframe[src*=…]` waits).
- Resolve the extension id from `context.serviceWorkers()[0].url()` (wait for
  the `serviceworker` event; fall back to `backgroundPages()` for MV2), then
  open `chrome-extension://<id>/popup.html` at popup size (e.g. 400×600) and
  options at ~800×600. Screenshot after `load` + a short settle.
- Seed state in the REAL page: `page.evaluate((data) => chrome.storage.local.set(data), seeds)`
  then `page.reload()` so the extension's own render code consumes it. Pass
  data as evaluate **arguments**, never string-interpolate into code.
- Keyboard-triggered behaviors may be modifier-gated per context (a plain key
  that works on iframe-hosted video may be ignored on a direct `<video>`) —
  read the handler code to pick the trigger that actually fires.
- Popup/options bodies often have no fixed height — a viewport screenshot pads
  them with dead whitespace. Capture `locator('body').screenshot()` (or the
  root container) to crop to content before compositing.
- sharp's `.flatten()` alone can still emit `hasAlpha: true` metadata — chain
  `.removeAlpha()` explicitly, and verify `metadata().hasAlpha === false` in
  the script's verify step.
- If the script runs under an esbuild-based runner (tsx), `page.evaluate`
  callbacks with inner functions throw `__name is not defined` — either use
  plain Node (`.mjs`), or `context.addInitScript({ content: 'globalThis.__name = globalThis.__name || ((fn) => fn);' })`.
- Composite with sharp: render an SVG frame (bg fill, optional radial glow,
  headline/subtitle `<text>` — **escape all text**) → PNG, then
  `.composite([{ input: capture, left, top }])`, then flatten. Derive frame
  colors from the extension's own palette; clamp text contrast ≥ 4.5:1.

## Script shape

```
scripts/screenshots.mjs      # or tests/screenshots.js
  captureAll()               # one persistent context; every raw capture
  stage per shot             # seeds + UI interactions + hide-banner tweaks
  composeAll()               # sharp frames: split | fullbleed | tile | marquee
  verify()                   # exact dims + no-alpha on every output, fail loudly
store-assets/                # committed outputs, regenerated by `npm run screenshots`
```

Keep capture and composition separate so palette/copy tweaks re-run in
milliseconds without re-driving the browser.
