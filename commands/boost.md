---
description: Set how your prompts get sharpened before Claude acts on them
argument-hint: [off|lite|full|ultra|status]
---

`/boost` is a switch, not a one-shot. It sets how **your request** is read —
it never changes how Claude writes its answer. The settings live in
`~/.claude/boost.json` and take effect on your next message.

Argument: $ARGUMENTS

## If the argument is `status`

Print the current settings and stop:

```bash
python3 -c "import json,os;p=os.path.expanduser('~/.claude/boost.json');print(open(p).read() if os.path.exists(p) else 'defaults: level=full mode=brief model=self')"
```

## If the argument is `off`, `on`, `lite`, `full` or `ultra`

Write it straight through — no picker, no questions. `on` means `full`.
Run this with LEVEL replaced by the chosen word:

```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser("~/.claude/boost.json")
try: cfg = json.load(open(p))
except Exception: cfg = {}
cfg["level"] = "LEVEL"
json.dump(cfg, open(p, "w"), indent=2)
print(json.dumps(cfg))
PY
```

Then confirm in one line what changed. Nothing else.

## If the argument is empty — the picker

**Your first action is a call to the `AskUserQuestion` tool** with the three
questions below, verbatim. Not a sentence of text first, not a Read: that tool
call. A bare `/boost` *is* the request for the picker, so asking is correct even
when the answer seems predictable.

    Q1 header "Strength", question "How hard should your prompts be sharpened?"
       - "full" — the whole brief (Recommended)
       - "lite" — one line only
       - "ultra" — the brief plus the biggest risk in the request
       - "off" — stop sharpening

    Q2 header "Kind", question "Sharpened how?"
       - "brief" — Goal / Done / Assume / Not (Recommended)
       - "rewrite" — one precise sentence naming the target and the artifact
       - "context" — fill in what the request leaves implicit

    Q3 header "Model", question "Who does the sharpening?"
       - "self" — Claude itself, no extra call, no added latency (Recommended)
       - "claude-haiku-4-5" — a separate fast model rewrites the prompt first
       - "claude-sonnet-5" — a separate stronger model rewrites the prompt first

Then write all three answers into the config in one call (same script as above,
with `cfg.update({"level": ..., "mode": ..., "model": ...})`), and confirm in
one line.

If the user picked a model other than `self`, add one line: it needs
`ANTHROPIC_API_KEY` in the environment, and falls back to `self` without it.

## Anything else as the argument

Treat it as a mistyped level: say so in one line and run the picker.

## Settings the picker does not cover

Both are edited directly in `~/.claude/boost.json`:

- `"style"` — free text appended to the sharpening instruction, e.g.
  `"prefer the smallest change that works"` or `"in german"`.
- `"show": true` — print the sharpened reading in the answer instead of
  keeping it internal. Off by default.
