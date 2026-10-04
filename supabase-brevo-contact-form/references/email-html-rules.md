# Email HTML rules

Email clients are not browsers. Gmail, Outlook, and Apple Mail each strip or
rewrite HTML/CSS differently, so the template in `email.ts` follows constraints
that would be unusual on the web. Keep them when editing.

## The rules

- **Tables for layout, not flexbox/grid.** `<table role="presentation">` with
  `cellpadding=0 cellspacing=0`. Flex and grid are unreliable (Outlook ignores
  them entirely).
- **Inline styles only.** No `<link>`, no `<style>` block, no classes — most
  clients strip `<head>` styles. Every element carries its own `style=""`.
- **No remote images for anything essential.** Images are blocked by default in
  many clients, so never convey required information (like the brand) with an
  image alone. Draw with background colours and text. If you must use a logo
  image, host it at an absolute HTTPS URL and keep meaningful text alongside it
  so a blocked image degrades gracefully.
- **System fonts.** `@font-face`/webfonts are widely ignored; use a system stack
  (already in `theme.ts`).
- **Always include a plain-text alternative.** `buildEmail` returns `text`
  alongside `html`; all three transports send both. It improves deliverability
  and covers text-only clients.
- **Inline dimensions on spacer/coloured cells.** A coloured `<td>` stretches to
  its row height — set explicit `width`/`height` and `font-size:0;line-height:0`
  on spacers, or shapes distort (e.g. dots rendering as ovals).
- **Escape user input.** `esc()` is applied to every record field. Never
  interpolate a raw submission into the HTML.

## Animated content

CSS animation doesn't run in email. The only broadly-supported animated format
is an **animated GIF**. Outlook shows only a GIF's first frame, so author the
first frame as the "resting" state you're happy to have shown statically.

## Previewing without sending

`email.ts` exports `buildEmail`, so you can render it locally with Deno:

```bash
deno eval --ext=ts "
import { buildEmail } from './supabase/functions/contact-notify/email.ts';
const { html } = buildEmail({ name:'Jane Doe', email:'jane@acme.com', project_type:'Web application', details:'Line one.\nLine two.' });
await Deno.writeTextFile('/tmp/email-preview.html', html);
"
open /tmp/email-preview.html
```

Always preview after editing the template — the failure modes (a stretched cell,
a blocked image) aren't visible in the source.
