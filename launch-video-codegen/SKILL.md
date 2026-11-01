---
name: launch-video-codegen
description: "Use when asked to create a launch video, demo video, or product promo (e.g. 'make a launch video for X'): build the motion sequence as a self-contained HTML page, record it headlessly with Playwright into an mp4, verify before sending. No video-generation API needed — works with any model and zero video credits."
---

# Launch Video via Codegen + Playwright Recording

Verified path for product launch/demo videos without a video-generation API (Z.AI video returns 429 insufficient-balance; LLM-only models cannot render video). Write the video as code, record it, verify, deliver.

## Procedure

1. **Storyboard** from the product: hook (the pain), fix (features), proof, end card (logo + tagline + CTA). Write the whole sequence as ONE self-contained HTML file — CSS keyframe scenes on a fixed 16:9 stage, a 20-30s looping timeline, no external dependencies (inline SVG, system fonts).
2. **Record with Playwright** (file:// URL — no HTTP server needed, and the server dies between turns):
   - Launch `chromium.launch({headless:true})`, `newContext({viewport:{width:1280,height:720}, recordVideo:{dir:'/tmp/rec', size:{width:1280,height:720}}})`.
   - `goto('file:///abs/path.html')`, wait the loop duration + buffer, `context.close()` to flush the webm.
3. **Convert + verify** (one step — always verify before sending):
   `ffmpeg -i /tmp/rec/*.webm -c:v libx264 -pix_fmt yuv420p -movflags +faststart out.mp4`
   Then `ffmpeg -v error -i out.mp4 -f null -` — **must print nothing** (decode_errors=0). Report duration + error count.

## Hard-won rules (each failure cost a round trip)

- **Long jobs must finish inside one turn.** A >20s node/playwright run gets backgrounded and killed at the turn boundary — twice leaving a truncated, unplayable mp4. Run the whole pipeline with a long `yieldMs` (≥95s) or in a persistent background job, never as a bare 25s sync exec.
- **The "running" status lies after a kill.** A ghost task can report "Generating/running" forever. Trust on-disk artifacts + ffprobe, not status.
- **Pick the right webm.** Multiple webms in the record dir = a killed attempt. `ffprobe` duration alone can lie (truncated containers report ~28s with 198 garbage frames). Only trust `ffmpeg -v error -i out.mp4 -f null -` output == 0 and a frame count close to duration × fps.
- Send the mp4 as `MEDIA:<abs path>` only after verification. Offer re-cuts (scene order, palette, length) — the HTML source re-renders in one command.

Source: Smart Video Controls launch video (Oct 2026) — v1 broken, v2 verified clean. Pairs with /brag-slim (latent-spaces/brag); this skill is the no-API implementation of that workflow.
