---
name: x-reader
description: Read X (Twitter) posts and threads by opening them in the browser. Use whenever a user shares an x.com or twitter.com link and wants to know what it says, what's being discussed, or wants help implementing/understanding something from a tweet. Handles modal dismissal (login prompts, cookie banners) automatically.
---

# X Reader

When the user shares an x.com or twitter.com link, open it in the browser and extract the content.

## Workflow

1. **Open the URL** in the host browser (profile omitted = openclaw managed browser):
   ```
   browser(action="open", url="<x_url>", target="host")
   ```

2. **Take a snapshot** to see the current page state:
   ```
   browser(action="snapshot", target="host")
   ```

3. **Dismiss any modals** (login prompts, cookie banners, "sign up to continue" overlays):
   - Look for close buttons, "Not now", "Dismiss", "Maybe later", "Accept all", or "X" buttons
   - Use `browser(action="act", request={kind:"click", ref:"<ref>"})` to dismiss
   - If a login wall blocks the full thread, you can still read the visible tweets

4. **Take another snapshot** after dismissal to get the clean page content

5. **Extract and summarize** what the tweet/thread says — text, images described, key points

## Tips

- X often shows a login modal on first visit — always check for and dismiss it before reading
- For threads, scroll down to get more replies if needed: `browser(action="act", request={kind:"press", key:"End"})`
- The `aria` refs mode is more stable: `browser(action="snapshot", refs="aria", target="host")`
- If the tweet contains a video, describe what's visible in the thumbnail/preview
- After reading, answer the user's actual question about the content
