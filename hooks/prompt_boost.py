#!/usr/bin/env python3
"""UserPromptSubmit hook: sharpens the user's request, and nothing else.

Settings live in ~/.claude/boost.json and are read fresh on every prompt:

    {"level": "full", "mode": "brief", "style": "", "model": "self", "show": false}

    level  off | lite | full | ultra   how hard to sharpen
    mode   brief | rewrite | context   what kind of sharpening
    style  free text                   appended to the instruction
    model  self | <anthropic model id> who rewrites; "self" adds no API call
    show   false | true                print the sharpened reading

With model "self" (the default) nothing extra runs: the main model reads its
own request more carefully. With a model id the prompt is rewritten through
the Anthropic API, which needs ANTHROPIC_API_KEY in the environment.

Nothing here touches how the answer is written - only how the request is read.

Self-check: python3 prompt_boost.py --selftest
"""
import json
import os
import re
import sys
import urllib.request

CONFIG = os.path.expanduser("~/.claude/boost.json")
DEFAULTS = {
    "level": "full",
    "mode": "brief",
    "style": "",
    "model": "self",
    "show": False,
    "timeout": 8,
    "max_tokens": 400,
}

# Acknowledgements, corrections and other non-briefs: nothing to sharpen.
CHATTER = re.compile(
    r"^\s*(ok(ay)?|ja|yes|no|nope|nein|yep|sure|weiter|go|continue|thx|thanks|"
    r"danke|stop|wait|warte|hm+|nice|perfect|passt)\b",
    re.I,
)

MODES = {
    "brief": "state it to yourself as Goal / Done / Assume / Not lines",
    "rewrite": "restate it as one precise sentence naming the target and the artifact",
    "context": "name what it leaves implicit: the file or area it points at, "
    "and what would count as done",
}

LEVELS = {
    "lite": " Keep it to one line.",
    "full": "",
    "ultra": " Also name the biggest risk in the request and the one thing"
    " that would show your reading is wrong.",
}

QUIET = """
Do this silently, as your own reading of the request. It is not part of your
answer: do not print it, and do not let it change your tone, format, length,
or how you work. Answer exactly as you would have without this note."""

LOUD = """
Put it in the first lines of your answer, then do the work. Nothing else about
your tone, format, length or process changes."""


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


def config() -> dict:
    """Settings from ~/.claude/boost.json, falling back to DEFAULTS."""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG) as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            cfg.update(loaded)
    except Exception:                # missing or broken file: run on defaults
        pass
    if cfg["mode"] not in MODES:
        cfg["mode"] = DEFAULTS["mode"]
    if cfg["level"] not in LEVELS and cfg["level"] != "off":
        cfg["level"] = DEFAULTS["level"]
    return cfg


def self_block(cfg: dict) -> str:
    style = f" {cfg['style'].strip()}" if cfg.get("style") else ""
    tail = LOUD if cfg.get("show") else QUIET
    return (
        "<prompt-boost>\n"
        f"Sharpen the user's request before acting on it: {MODES[cfg['mode']]}."
        f"{LEVELS[cfg['level']]}{style}\n{tail}\n</prompt-boost>"
    )


def api_block(sharpened: str, cfg: dict) -> str:
    return (
        "<prompt-boost>\n"
        f"A sharpened reading of the user's request, written by {cfg['model']}"
        " and not by the user:\n\n"
        f"{sharpened}\n\n"
        "Use it as your reading of the request. Where it and the user's own"
        " message differ, the user's message wins. Your tone, format, length"
        " and process are unaffected by this note.\n</prompt-boost>"
    )


def rewrite(prompt: str, cfg: dict):
    """Rewrite the prompt through the API. None on any failure - prompt stays as typed."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    system = (
        f"Rewrite the user's request so it is precise: {MODES[cfg['mode']]}."
        f"{LEVELS[cfg['level']]} {cfg.get('style', '')}\n"
        "Output only the rewritten request. Add no commentary, no preamble, and"
        " no instructions about how an answer should be written. Keep the"
        " user's language and intent; fill gaps with the most likely reading"
        " and mark each one as an assumption."
    )
    body = json.dumps({
        "model": cfg["model"],
        "max_tokens": cfg["max_tokens"],
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as r:
            data = json.load(r)
        text = "".join(b.get("text", "") for b in data.get("content", [])).strip()
        return text or None
    except Exception:
        return None


def selftest() -> None:
    for p in ("", "ok", "/boost ultra", "what does this function do?",
              "danke, das passt so", "fix it"):
        assert skip(p), p
    for p in ("make the dashboard better", "clean up the parser and speed it up"):
        assert not skip(p), p

    cfg = dict(DEFAULTS)
    block = self_block(cfg)
    assert "do not print it" in block and "Goal / Done" in block
    assert "one line" in self_block({**cfg, "level": "lite"})
    assert "biggest risk" in self_block({**cfg, "level": "ultra"})
    assert "first lines of your answer" in self_block({**cfg, "show": True})
    assert "one precise sentence" in self_block({**cfg, "mode": "rewrite"})
    assert "in german" in self_block({**cfg, "style": "in german"})
    assert "user's message wins" in api_block("Goal: x", cfg)

    assert config()["level"] in LEVELS or config()["level"] == "off"
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        return selftest()
    prompt = json.load(sys.stdin).get("prompt", "")
    cfg = config()
    if cfg["level"] == "off" or skip(prompt):
        return
    if cfg["model"] != "self":
        sharpened = rewrite(prompt, cfg)
        if sharpened:
            print(api_block(sharpened, cfg))
            return                   # no key or API down: fall through to self
    print(self_block(cfg))


if __name__ == "__main__":
    main()
