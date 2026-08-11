---
description: Sharpen a vague request into a precise brief, then do the work
argument-hint: [lite|full|ultra] <your request>
---

Raw request: $ARGUMENTS

If it is empty, use the user's last message in this conversation instead.
If it starts with `lite`, `full` or `ultra`, that word is the level, not part of the request.

## Step 0 — pick the settings

Only when the raw request is empty (bare `/boost` + Enter): before anything else,
call `AskUserQuestion` once with these two questions, then obey the answers.
If the raw request has text, skip this step entirely — never ask.

    Q1 header "Strength", question "How sharp should the brief be?"
       - "full — the four-line brief (Recommended)"
       - "lite — the Goal line only"
       - "ultra — brief + 3-5 steps + the biggest risk"

    Q2 header "Mode", question "And then?"
       - "Brief + do the work (Recommended)"
       - "Brief only — emit it and stop, no edits, no tools"

## Step 1 — sharpen

Emit only the lines that carry information. Drop the ones you have nothing to put in.

    Goal:   <verb> <object> in <file/area> → <artifact someone can point at>
    Done:   <the check that proves it: a command, a test, an observable behavior>
    Assume: <gap filled with the most likely reading>
    Not:    <adjacent work you are deliberately leaving out>

Rules:

- Translate vague verbs into checkable outcomes:
  - "better / cleaner / nicer" → name the property that changes
  - "fix" → name the symptom and the expected output
  - "add X" → name the call site and the signature
  - "optimize" → name what gets measured, and against what
- Fill gaps with the most likely reading and label it `Assume:`. Do not ask.
- Ask exactly ONE question only when two readings lead to fundamentally different
  work — your recommendation first. Otherwise, none.
- If the target is unclear, find it in the code *before* writing the Goal line.
  A brief pointing at the wrong file is worse than a vague one.
- `Not:` is for scope the request plausibly implies but you are skipping. Leave it
  out rather than inventing something to reject.
- No prose, no preamble, no restating the request back.

Levels:

- `lite` — the Goal line, nothing else.
- `full` — the block above. Default.
- `ultra` — the block, plus 3-5 numbered steps, plus one line naming the biggest
  risk and how it would show up.

## Step 2 — do the work

Immediately. The brief replaces nothing — it is the first line of the answer, not
the answer. Deliver the whole Goal; if part of it turns out to be blocked, finish
the rest and say plainly what you left out and why.
