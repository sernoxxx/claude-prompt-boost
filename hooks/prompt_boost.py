#!/usr/bin/env python3
"""UserPromptSubmit hook: appends a refinement instruction to vague prompts.

No second LLM call - the main model sharpens its own brief, with full context.
Self-check: python3 prompt_boost.py --selftest
"""
import json
import re
import sys

# Acknowledgements, corrections and other non-briefs: nothing to sharpen.
CHATTER = re.compile(
    r"^\s*(ok(ay)?|ja|yes|no|nope|nein|yep|sure|weiter|go|continue|thx|thanks|"
    r"danke|stop|wait|warte|hm+|nice|perfect|passt)\b",
    re.I,
)


def skip(prompt: str) -> bool:
    """True when the prompt is not a work request worth sharpening."""
    p = prompt.strip()
    if not p or p[0] in "/!#":       # slash command, bash passthrough, memory note
        return True
    if len(p.split()) < 3:           # "fix it", "run tests": nothing to sharpen
        return True
    if p.rstrip().endswith("?"):     # a question wants an answer, not a brief
        return True
    return bool(CHATTER.match(p))


REFINEMENT = """<prompt-refinement>
Before acting, sharpen the brief. Emit only the lines that carry information:

Goal:   <verb> <object> in <file/area> -> <artifact someone can point at>
Done:   <the check that proves it: a command, a test, an observable behavior>
Assume: <gap filled with the most likely reading>
Not:    <adjacent work you are deliberately leaving out>

Translate vague verbs ("better", "fix", "optimize") into checkable outcomes.
Fill gaps with the most likely reading and label it `Assume:` - do not ask.
One question only when two readings lead to fundamentally different work.
If the target is unclear, locate it in the code before writing the Goal line.
No prose, no preamble, no restating the request. Then work - the brief
replaces nothing.
</prompt-refinement>"""


def main() -> None:
    if "--selftest" in sys.argv:
        for p in ("", "ok", "/boost do a thing", "what does this function do?",
                  "danke, das passt so", "fix it"):
            assert skip(p), p
        for p in ("make the dashboard better", "make the login page better somehow",
                  "clean up the parser and speed it up"):
            assert not skip(p), p
        print("selftest ok")
        return
    if not skip(json.load(sys.stdin).get("prompt", "")):
        print(REFINEMENT)


if __name__ == "__main__":
    main()
