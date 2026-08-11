#!/usr/bin/env python3
"""UserPromptSubmit hook: sharpens the user's request. Nothing else.

The hook only ever shapes how the request is read. It says nothing about tone,
format, length, verbosity or how to work - answers come out exactly as they
would have without it.

What happens when you hit enter with `/boost <prompt>` (or `/boost-mini
<prompt>`, which forces the grammar-only mode for that one prompt):

    your prompt  ->  rewritten by a second model  ->  the original is blocked,
    and the rewrite lands in your input box in the same session

Nothing is sent until you press enter yourself, so you always see and can edit
the request the model will actually get.

Settings live in ~/.claude/boost.json and are only ever changed by the `/boost`
picker - one way to set this up, not three.

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
POWERSHELL = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
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
    "mini": "Rewrite it only for grammar and sentence structure: fix mistakes,"
    " straighten word order, split run-on sentences, drop filler. Keep every"
    " word that carries meaning, add nothing, fill no gaps.",
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


# /boost-mini forces the grammar-only mode for one prompt, settings untouched.
PREFIXES = (("/boost-mini ", "mini"), ("/boost ", None))


def strip_prefix(prompt: str):
    """The request behind the /boost prefix and the mode it forces, or None."""
    p = prompt.strip()
    for prefix, mode in PREFIXES:
        if p.startswith(prefix):
            return p[len(prefix):], mode
    return None


def skip(prompt: str) -> bool:
    """True when the prompt is not a /boost work request worth rewriting."""
    hit = strip_prefix(prompt)
    if hit is None:
        return True
    actual = hit[0]
    if len(actual.split()) < 3:
        return True
    if actual.rstrip().endswith("?"):
        return True
    return bool(CHATTER.match(actual))


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
    if cfg["model"] == "self":       # dropped: leaves nothing to hand back
        cfg["model"] = DEFAULTS["model"]
    return cfg


def save(**fields) -> dict:
    cfg = config()
    cfg.update(fields)
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg


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
    level = "" if cfg["mode"] == "mini" else LEVELS[cfg["level"]]
    return "\n".join(
        [RULES, MODES[cfg["mode"]], level, cfg.get("style", "")]
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


# --- getting the rewrite into your input box -----------------------------

def keys_escape(text: str) -> str:
    """SendKeys reads +^%~(){}[] as commands; braces around them mean literal."""
    return "".join("{%s}" % c if c in "+^%~(){}[]" else c for c in text)


def hand_to_input_box(text: str) -> bool:
    """Put the rewrite in the input box, unsent.

    No hook output can fill that box, so this goes the way you would: the same
    key events, sent to the foreground window - the terminal you just hit enter
    in. Windows only (WSL counts); False anywhere else, and the caller then
    falls back to the old inline behaviour.

    Line breaks are flattened to spaces on purpose: a line break here is an
    enter, and that would send the prompt instead of leaving it to you.
    """
    if not os.path.exists(POWERSHELL):
        return False
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write(keys_escape(" ".join(text.split())))
        win = subprocess.run(["wslpath", "-w", f.name],
                             capture_output=True, text=True).stdout.strip()
        subprocess.Popen(
            [POWERSHELL, "-NoProfile", "-Command",
             f"$w = New-Object -ComObject wscript.shell;"
             f"$w.SendKeys([IO.File]::ReadAllText('{win}'));"
             f"Remove-Item -LiteralPath '{win}'"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:
        return False


# --- /boost command ------------------------------------------------------

PICKER = f"""BOOST SETTINGS PICKER

Call the `AskUserQuestion` tool RIGHT NOW, as the very first thing you do, with
exactly the three questions below. Write no text before the tool call. The user
typed `/boost`, which is a request for this picker - asking is correct even when
the answer looks predictable. Anything typed after `/boost` is not a setting:
this picker is the only way in.

Q1 header "Strength", question "How far should your prompts be rewritten?"
   - "full" - fill gaps and mark them as assumptions (Recommended)
   - "lite" - one sentence, change as little as possible
   - "ultra" - full, plus the biggest risk in the request
   - "off" - stop rewriting

Q2 header "Kind", question "Rewritten into what?"
   - "rewrite" - a precise request naming target and artifact (Recommended)
   - "brief" - Goal / Done / Assume / Not
   - "context" - the same request with the implicit parts spelled out
   - "mini" - grammar and sentence structure only, nothing added

Q3 header "Model", question "Who rewrites the prompt?"
   - "sonnet" - rewrites on your subscription, ~8s (Recommended)
   - "haiku" - faster, but often answers or asks instead of rewriting

Then save all three answers with ONE Bash call, substituting the picked values:

    python3 "{SELF}" --set level=<Q1> mode=<Q2> model=<Q3>

Finally tell the user in one line what is now set. Nothing more."""


def selftest() -> None:
    global CONFIG                    # never write the real settings from a test
    CONFIG = os.path.join(tempfile.gettempdir(), "boost-selftest.json")
    for p in ("", "/boost ultra", "/boost was ist das?", "danke, das passt so", "/boost fix it"):
        assert skip(p), p
    for p in ("/boost make the dashboard better", "/boost clean up the parser and speed it up",
              "/boost-mini fix the parser bug"):
        assert not skip(p), p
    assert strip_prefix("/boost-mini fix the parser") == ("fix the parser", "mini")
    assert strip_prefix("/boost fix the parser") == ("fix the parser", None)
    assert strip_prefix("/boosted thing") is None

    assert "AskUserQuestion" in PICKER
    assert "self" not in PICKER.split('Q3')[1]     # one rewriter question, no self
    assert config()["level"] in tuple(LEVELS) + ("off",)
    assert config()["model"] != "self"

    assert keys_escape("a+b{c}") == "a{+}b{{}c{}}"
    assert keys_escape("plain text") == "plain text"

    mini = {**config(), "mode": "mini", "level": "ultra"}
    assert "grammar" in system_prompt(mini).lower()
    assert "risk" not in system_prompt(mini).lower()      # level stays out of mini

    # The API path stays silent without a key; main() then falls back to the CLI.
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    assert rewrite("make the parser faster", config()) is None
    if saved is not None:
        os.environ["ANTHROPIC_API_KEY"] = saved
    os.path.exists(CONFIG) and os.remove(CONFIG)
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        return selftest()
    if "--cmd" in sys.argv:          # /boost, whatever was typed after it
        return print(PICKER)
    if "--set" in sys.argv:
        fields = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--set") + 1:]
                      if "=" in a)
        fields = {k: v for k, v in fields.items() if k in DEFAULTS}
        return print(json.dumps(save(**fields)))

    prompt = json.load(sys.stdin).get("prompt", "")
    cfg = config()
    if cfg["level"] == "off" or os.environ.get("BOOST_CHILD"):
        return
    hit = strip_prefix(prompt)
    if hit is None or skip(prompt):
        return
    actual_prompt, forced = hit
    if forced:
        cfg = {**cfg, "mode": forced}
    sharper = (rewrite if os.environ.get("ANTHROPIC_API_KEY") else cli_rewrite)(actual_prompt, cfg)
    if not sharper:                  # rewriter down: let the original through
        return
    if not hand_to_input_box(sharper):
        return print(f"<boosted-prompt>\n{sharper}\n</boosted-prompt>")
    print(json.dumps({
        "decision": "block",
        "reason": "Boosted. The rewrite is waiting in your input box - press enter to send it:\n\n" + sharper,
    }))


if __name__ == "__main__":
    main()
