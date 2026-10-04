---
name: compaction
description: Auto-suggest context compaction when API rate limits are hit. Use when the agent encounters "API rate limit reached" or similar rate-limit errors, or when context window is likely full. Triggers on: rate limit errors, context length errors, token limit exceeded, or any 429-style API responses.
---

# Compaction

When you encounter an API rate limit or context-length error (e.g. "⚠️ API rate limit reached"), the likely cause is a full context window — not an actual rate limit.

## What to do

1. Reply to the user: "Context is looking full — run `/compact` to free up space, then we're good to go."
2. Do NOT retry the request or explain rate limiting in detail. The fix is compaction.

## When this applies

- Any message containing "rate limit" or "API rate limit reached"
- Token/context length exceeded errors
- Repeated failures after long conversations

## After compaction

Once the user runs `/compact`, the conversation history is summarized and context is freed. Continue the task normally.
