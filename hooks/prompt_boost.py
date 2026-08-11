#!/usr/bin/env python3
"""UserPromptSubmit hook: sharpens the user's request. Nothing else.

The hook only ever shapes how the request is read. It says nothing about tone,
format, length, verbosity or how to work - answers come out exactly as they
would have without it.

Settings live in ~/.claude/boost.json and are read fresh on every prompt:

    {"level": "full", "mode": "rewrite", "style": "", "model": "self"}

    level  off | lite | full | ultra    how far to push it
    mode   rewrite | brief | context    what the request turns into
    style  free text                    extra steering
    model  self | an Anthropic model id who does the sharpening

With model "self" (the default) the answering model restates the request
itself: no API key, no second call, no added latency. Set a model id instead
and the prompt is rewritten through the Anthropic API first, which needs
ANTHROPIC_API_KEY - without it, or on any failure, "self" takes over.

Self-check: python3 prompt_boost.py --selftest
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

CONFIG = os.path.expanduser("~/.claude/boost.json")
CREDS = os.path.expanduser("~/.claude/.credentials.json")
CHILD = os.path.expanduser("~/.claude/boost-child")
SELF = os.path.abspath(__file__)
DEFAULTS = {
    "level": "full",
    "mode": "rewrite",
    "style": "",
    "model": "sonnet",
    "timeout": 25,
    "max_tokens": 600,
}

# Acknowledgements, corrections and other non-briefs: nothing to rewrite.
CHATTER = re.compile(
    r"^\s*(ok(ay)?|ja|yes|no|nope|nein|yep|sure|weiter|go|continue|thx|thanks|"
    r"danke|stop|wait|warte|hm+|nice|perfect|passt)\b",
    re.I,
)

MODES = {
    "rewrite": "Rewrite it as a precise request: name the target (file, area,"
    " component) and the artifact that should exist afterwards.",
    "brief": "Rewrite it as a brief with the lines Goal / Done / Assume / Not:"
    " what to do, the check that proves it, the gap you filled, the adjacent"
    " scope left out. Drop any line you have nothing to put in.",
    "context": "Rewrite it with what it leaves implicit spelled out: which"
    " file or area it points at, and what would count as done.",
}

LEVELS = {
    "lite": "Keep it to one sentence. Change as little as possible.",
    "full": "Make every gap you fill explicit as an assumption.",
    "ultra": "Make every gap you fill explicit as an assumption, and add the"
    " single biggest risk in the request.",
}

RULES = (
    "You rewrite prompts. The user's message is a request they are about to"
    " send to a coding agent, and your output replaces it verbatim.\n"
    "Output the rewritten request and nothing else: no preamble, no"
    " commentary, no quotes around it, no explanation of what you changed.\n"
    "Keep the user's language, intent and scope. Do not answer the request,"
    " do not solve it, and do not add instructions about how the answer should"
    " be written, formatted or toned - you are improving the question, not"
    " shaping the reply.\n"
    "Keep the rewrite compact: under 100 words unless the original is longer.\n"
    "Never ask a question and never address the user - you are not talking to"
    " them, you are producing the text they will send. If a detail is missing,"
    " fill it with the most likely reading and mark it as an assumption."
)

LEVEL_WORDS = ("off", "on", "lite", "full", "ultra")


def skip(prompt: str) -> bool:
    """True when the prompt is not a work request worth rewriting."""
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


def save(**fields) -> dict:
    cfg = config()
    cfg.update(fields)
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg


def self_block(cfg: dict) -> str:
    """The keyless path: the answering model restates the request itself.

    Two sentences, both about reading the request. Nothing about tone, format,
    length or process - that is what made v1 change how answers were written.
    """
    style = f" {cfg['style'].strip()}" if cfg.get("style") else ""
    return (
        f"<boost>\nBefore acting, restate the request above to yourself"
        f" {MODES[cfg['mode']].replace('Rewrite it ', '')}"
        f" {LEVELS[cfg['level']]}{style}\n"
        "That restatement is only your reading of the request.\n</boost>"
    )


def child_env() -> dict:
    """A config dir of its own for the rewriter: your login, none of your hooks.

    Pointing CLAUDE_CONFIG_DIR at an empty dir keeps the session hooks from
    firing in the child (they would block on a permission prompt and take 40s).
    The credentials symlink is what keeps this on your subscription instead of
    wanting an API key.
    """
    os.makedirs(CHILD, mode=0o700, exist_ok=True)
    link = os.path.join(CHILD, ".credentials.json")
    if not os.path.lexists(link):
        os.symlink(CREDS, link)
    settings = os.path.join(CHILD, "settings.json")
    if not os.path.exists(settings):
        with open(settings, "w") as f:
            f.write("{}")
    return {**os.environ, "CLAUDE_CONFIG_DIR": CHILD, "BOOST_CHILD": "1"}


def cli_rewrite(prompt: str, cfg: dict):
    """Rewrite through the Claude CLI - your subscription, no API key."""
    try:
        out = subprocess.run(
            ["claude", "-p", "--model", cfg["model"],
             "--system-prompt", system_prompt(cfg),
             "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}'],
            input=prompt,
            capture_output=True, text=True, timeout=cfg["timeout"],
            env=child_env(), cwd=CHILD,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def system_prompt(cfg: dict) -> str:
    return "\n".join(
        [RULES, MODES[cfg["mode"]], LEVELS[cfg["level"]], cfg.get("style", "")]
    ).strip()


def rewrite(prompt: str, cfg: dict):
    """The rewritten prompt, or None on any failure - caller then stays silent."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    system = system_prompt(cfg)
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


# --- /boost command ------------------------------------------------------

PICKER = f"""BOOST SETTINGS PICKER

Call the `AskUserQuestion` tool RIGHT NOW, as the very first thing you do, with
exactly the three questions below. Write no text before the tool call. The user
typed a bare `/boost`, which is a request for this picker - asking is correct
even when the answer looks predictable.

Q1 header "Strength", question "How far should your prompts be rewritten?"
   - "full" - fill gaps and mark them as assumptions (Recommended)
   - "lite" - one sentence, change as little as possible
   - "ultra" - full, plus the biggest risk in the request
   - "off" - stop rewriting

Q2 header "Kind", question "Rewritten into what?"
   - "rewrite" - a precise request naming target and artifact (Recommended)
   - "brief" - Goal / Done / Assume / Not
   - "context" - the same request with the implicit parts spelled out

Q3 header "Model", question "Who rewrites the prompt?"
   - "sonnet" - Sonnet rewrites it first, on your subscription, ~8s (Recommended)
   - "self" - no separate call and no wait: the answering model restates it itself
   - "haiku" - faster, but often answers or asks instead of rewriting

Then save all three answers with ONE Bash call, substituting the picked values:

    python3 "{SELF}" --set level=<Q1> mode=<Q2> model=<Q3>

Finally tell the user in one line what is now set. Nothing more."""


def command(arg: str) -> str:
    arg = arg.strip().lower()
    if arg == "status":
        cfg = config()
        key = "set" if os.environ.get("ANTHROPIC_API_KEY") else "MISSING"
        return (
            "Report these settings to the user in one short block, nothing else:\n"
            f"level={cfg['level']} mode={cfg['mode']} model={cfg['model']}\n"
            f"style={cfg['style'] or '(none)'}\n"
            f"ANTHROPIC_API_KEY={key}"
            + ("\nWithout the key nothing is rewritten." if key == "MISSING" else "")
        )
    if arg in LEVEL_WORDS:
        cfg = save(level="full" if arg == "on" else arg)
        return (
            f"Boost level is now '{cfg['level']}'. Tell the user that in one"
            " line and stop. Do not call any other tool."
        )
    if arg:
        return f"'{arg}' is not a level. Say so in one line, then:\n\n{PICKER}"
    return PICKER


def selftest() -> None:
    global CONFIG                    # never write the real settings from a test
    CONFIG = os.path.join(tempfile.gettempdir(), "boost-selftest.json")
    for p in ("", "ok", "/boost ultra", "what does this function do?",
              "danke, das passt so", "fix it"):
        assert skip(p), p
    for p in ("make the dashboard better", "clean up the parser and speed it up"):
        assert not skip(p), p

    assert "AskUserQuestion" in command("")
    assert "AskUserQuestion" in command("bogus") and "not a level" in command("bogus")
    assert "level=" in command("status")
    for w in LEVEL_WORDS:
        assert "now" in command(w)
    assert config()["level"] in tuple(LEVELS) + ("off",)

    cfg = config()
    block = self_block(cfg)
    for banned in ("tone", "format", "length", "concise", "preamble", "prose"):
        assert banned not in block.lower(), banned
    assert "restate the request" in block.lower()
    assert "one sentence" in self_block({**cfg, "level": "lite"}).lower()
    assert "goal / done" in self_block({**cfg, "mode": "brief"}).lower()

    # The API path stays silent without a key; main() then falls back to self.
    saved, os.environ["ANTHROPIC_API_KEY"] = os.environ.pop("ANTHROPIC_API_KEY", None), ""
    del os.environ["ANTHROPIC_API_KEY"]
    assert rewrite("make the parser faster", config()) is None
    if saved is not None:
        os.environ["ANTHROPIC_API_KEY"] = saved
    os.path.exists(CONFIG) and os.remove(CONFIG)
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        return selftest()
    if "--cmd" in sys.argv:
        i = sys.argv.index("--cmd")
        return print(command(sys.argv[i + 1] if len(sys.argv) > i + 1 else ""))
    if "--set" in sys.argv:
        fields = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--set") + 1:]
                      if "=" in a)
        fields = {k: v for k, v in fields.items() if k in DEFAULTS}
        return print(json.dumps(save(**fields)))

    prompt = json.load(sys.stdin).get("prompt", "")
    cfg = config()
    if cfg["level"] == "off" or skip(prompt) or os.environ.get("BOOST_CHILD"):
        return
    if cfg["model"] != "self":
        sharper = (rewrite if os.environ.get("ANTHROPIC_API_KEY") else cli_rewrite)(prompt, cfg)
        if sharper:
            return print(f"<boosted-prompt>\n{sharper}\n</boosted-prompt>")
    print(self_block(cfg))           # rewriter unavailable: the model does it itself


if __name__ == "__main__":
    main()
