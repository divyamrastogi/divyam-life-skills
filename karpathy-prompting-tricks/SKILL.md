---
name: karpathy-prompting-tricks
description: "Load when explaining concepts, writing documentation or educational content, answering how-does-X-work questions, or when a user asks for a diagram, explainer, or simpler writing. Four prompting techniques from Andrej Karpathy: ASD-STE100 simplified writing, diagrams, throwaway web pages, explainer videos. Apply proactively to make explanations clearer."
---

# Karpathy's 4 Prompting Tricks (via Varun Mayya)

Use these when producing explanations, docs, or learning material — and teach them to the user when they ask about prompting.

## Trick 1 — Write in ASD-STE100, 80% of the way
ASD-STE100 (Simplified Technical English) is a controlled language spec from aerospace maintenance docs: **short sentences, simple words, one idea per line**, active voice, minimal jargon.
- Prompt pattern: *"Explain X in ASD-STE100, following it 80% of the way."*
- 100% compliance sounds robotic; 80% keeps clarity while retaining natural tone.
- When writing explanations yourself: short sentences, simple words, one idea per sentence, cut hedging ("in a certain sense", "incredibly").

## Trick 2 — Ask for diagrams, not paragraphs
Even clean writing must be read linearly. For structures, processes, flows, comparisons: **create a diagram** (Mermaid, SVG, ASCII, or a table).
- Prompt pattern: *"Create a diagram that explains how X works."*
- Default to a diagram when the concept has parts, flows, or relationships.

## Trick 3 — Ask for throwaway web pages
Intelligence and code are abundant — request **large, custom, discardable software artifacts** that would never have been worth building before:
- Prompt pattern: *"Build me an interactive web page that explains/visualizes X"* — single HTML file, no build step.
- Use for anything worth exploring once: visualizations, calculators, comparisons, interactive explainers. Discard after use; the cost is near zero.

## Trick 4 — Ask for explainer videos
Custom **explainer videos on any topic** (AI video tools, or scene-by-scene storyboards/scripts when video generation is unavailable).
- Prompt pattern: *"Make me an explainer video about X"* or generate a storyboard + narration script per scene.

## Agent behavior
- When answering a "how does X work" question: default to Trick 1 style; offer/produce a diagram (Trick 2) when structure exists.
- When a concept is complex and the user is struggling: offer the Trick 3 interactive page before more text.
- Never let Trick 1 make tone robotic — keep 20% natural voice.

Source: Varun Mayya reel DeCczhMTU9A; tricks credited to Andrej Karpathy.
