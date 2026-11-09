---
name: ui-animation-rules
description: "MUST load before writing ANY UI code — mobile or web (HTML/CSS/JS, React, Next.js, Flutter, Swift, Android). The 20 animation rules for beautiful, polished UI motion: easing, stagger, presses, popovers, exits, masks, crossfades, rubber-banding, shared-element transitions — plus the concentric border-radius nesting rule and 20 UX polish patterns (skeletons, optimistic updates, command menu, undo toasts, view transitions, hit slop, tabular numbers and more). Apply proactively and automatically; never wait to be asked. Companion to interface-design-rules (layout/type/color)."
---

# UI Animation Rules — The 20 Rules for Beautiful UI Motion

Apply these defaults whenever generating or reviewing ANY interface code — web or mobile. They are defaults, not suggestions; deviate only with a stated reason. Source: "20 Ways to Make Beautiful AI Animations" (verified frame-by-frame).

## The 20 Rules

**Timing & easing**
1. **Ease-out for entrances** — objects decelerate into place; never linear, never ease-in for anything appearing.
2. **Dropdowns at 150–250ms** — menus open fast; slower feels laggy, faster feels jumpy.
3. **Stagger list rows by 30ms** — sequential reveal, top to bottom. Constant offset, not proportional.
6. **Stagger as details settle** — primary content first, secondary details follow in the same stagger wave.
9. **Ease-in-out for moves** — on-screen movements (position changes, reorders) use ease-in-out, not ease-out.
15. **Make exits ~20% shorter than entrances** — leaving should feel faster than arriving.

**Presses, knobs & feedback**
4. **Scale to 0.97 on press** — buttons press down to `scale(0.97)`, ~150ms, restore on release.
5. **Stretch moving knobs 12%** — knobs/handles stretch in their direction of travel by ~12% while moving, settle back at rest.
8. **Pulse to confirm success** — a single pulse/scale-flash confirms success states (saved, sent, copied). No spinners for done.
13. **No bounce on everyday UI** — no springy overshoot for menus, modals, buttons. Springs are for playful, deliberate moments only.
14. **Don't tween while held** — while the user holds/drags, track the pointer directly (no lag/tween); tween only on release.
19. **Rubber band past bounds** — at drag limits, allow slight overscroll resistance (iOS-style), then snap back.

**Entry, exit & position**
7. **Arcs for object movement** — objects moving across the screen travel on a slight arc, not a straight line.
10. **Start popovers at scale 0.95** — popovers/menus scale in from 0.95 → 1.0 with fade.
11. **Enter from the trigger** — set transform-origin (web) / anchor point to the triggering element, never center-of-screen.
12. **Exit to the trigger** — reversals collapse back toward their trigger, not wherever they appeared.
16. **Overlap old & new states** — crossfade/overlap state changes instead of blank gaps; old state leaves as new state arrives.

**Structure & identity**
17. **Masks for reveals & colour changes** — clip/mask text and content changes instead of crossfading opacity (e.g. tab-label swaps: clip the old text out, new text in).
18. **Crossfade icons + blur** — icon swaps crossfade with a slight scale and blur for a glassy handoff.
20. **Reuse the same layoutId / shared element** — when an object persists across states (card → detail page), animate THE SAME element expanding (`layoutId` in Framer Motion, `Hero` in Flutter, ActivityOptions in Android) — never a disconnected replacement.

## Implementation cheat-sheet

**Web (CSS/React):**
- Entrances: `transition: opacity 200ms ease-out, transform 200ms ease-out`
- Moves: `transition: transform 300ms ease-in-out`
- Press: `active { transform: scale(0.97) }` + `transition: scale 150ms ease-out`
- Stagger: `animation-delay: calc(var(--i) * 30ms)`
- Shared elements: Framer Motion `layoutId` (or View Transitions API `view-transition-name`)
- Exits: `transform + opacity + blur(4px)`, duration = entrance × 0.8
- NEVER `transition: all` — name exact properties (from interface-design-rules)

**Mobile (Flutter):**
- Entrances: `Curves.easeOutCubic`, 200ms
- Moves/reorders: `Curves.easeInOut`, 300ms
- Press: `scale 0.97` via AnimatedScale/ScaleTransition, 150ms
- Shared element: `Hero` widget with matching `tag`
- Stagger: `Interval(0, 1, curve:)` per item, 30ms offset via `DelayedAnimation`
- Overscroll: default `BouncingScrollPhysics` (iOS-look) already rubber-bands
- Exits: route reverse duration × 0.8

**SwiftUI:** `.spring(response:0.3)` only for deliberate moments; default `.easeOut`; `matchedGeometryEffect(id:)` for rule 20.

## Frequency-based exception (from interface-design-rules)
Frequently-opened menus: skip the open animation, animate the close only.

## Stability & hygiene (web)
- **Never `transition: all`** — name exact properties.
- **No transitions when switching light/dark mode** — disable them across the theme swap.
- **Nothing animates on page load** unless intentional; hover/frequent interactions stay instant.
- Flicker while animating? Add `will-change: transform` (especially iOS Safari).
- Wrap animations in `@media (prefers-reduced-motion: no-preference)`.

## Geometry & radii (static, not motion)

**Concentric corner rule** — when a rounded element (button, input, thumbnail) sits inside a rounded container (card, sheet), the corners must nest: **`outer radius = inner radius + padding`**. Example: card padding 8px + button radius 20px → card radius 28px. Equal radii on nested elements look subtly "off" — the inner corner bulges against the outer curve. Nest it right and everything looks clean and intentional. Applies to all platforms (CSS `border-radius`, Flutter `BorderRadius`, SwiftUI `cornerRadius`).

## 20 UX polish patterns (apply when relevant, not just motion)

1. **Skeleton loaders** — shape-matching placeholders instead of spinners; no layout shift when data lands.
2. **Optimistic updates** — render the result immediately, roll back on failure (likes, toggles, reorders).
3. **Command menu** — ⌘K/Ctrl+K palette for navigation and actions in any app with >5 destinations.
4. **Shortcut hints** — show the keyboard shortcut inside tooltips/menu items.
5. **Undo toasts** — destructive actions get a toast with Undo (5–10s); never a confirm() dialog.
6. **Stale-while-revalidate** — show cached data instantly, refresh in background, swap when fresh.
7. **Pre-rendering** — prefetch/predict the likely next screen (hover, route idle, list-adjacent items).
8. **BlurHash placeholders** — tiny blurred hash for images before load; never an empty grey box.
9. **View transitions** — animate route/page changes (View Transitions API / shared elements), not hard cuts.
10. **Swipe-to-dismiss sheets** — drag down/back to close; velocity-based, matches gesture.
11. **Interruptible animations** — user input cancels/reverses mid-flight; never lock the UI while animating.
12. **Predictive back** — Android/iOS back-gesture preview animates the actual destination state.
13. **Hit slop** — touch targets ≥44×44pt; enlarge the tappable area beyond the visual icon (~8–12px).
14. **Safe area insets** — respect notches/home bars/keyboards via env(safe-area-inset-*) / SafeArea widgets.
15. **One-time code autofill** — OTP fields declare `autocomplete="one-time-code"` (web) / `oneTimeCode` content type (iOS) for SMS autofill.
16. **Tabular numbers** — `font-variant-numeric: tabular-nums` for any changing/aligned figures (prices, timers, tables).
17. **Balanced headlines** — `text-wrap: balance` on headings; no orphaned last words.
18. **Continuous corners** — iOS-style smooth corner curvature (squircles) on nested/adjacent rounded elements.
19. **Idempotency keys** — every submit/network action carries an idempotency key; double-tap can't double-charge.
20. **Amazon safe triangle** — dropdowns/submenus navigable without crossing off the trigger (pointer-triangle hit region, or add a 150–300ms hover delay before closing).

Apply these as defaults when building: loaders → skeletons, mutations → optimistic + undo, forms → autofill + idempotency, data views → stale-while-revalidate + tabular nums, navigation → command menu + view transitions.

## Self-invocation contract
This skill applies AUTOMATICALLY whenever generating, modifying, or reviewing: HTML/CSS/JS, React/Next/Vue components, Flutter widgets, SwiftUI/Compose views, landing pages, dashboards, emails with styling, or any file containing transitions/animations. If you notice UI work in progress without these rules applied, retrofit them before finishing.
