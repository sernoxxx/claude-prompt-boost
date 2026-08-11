# prompt-boost

Most bad agent output starts with a bad brief. You type *"clean up the parser"*,
the model picks one of five readings, and you find out which one after it has
rewritten a file you liked.

`prompt-boost` makes the model state the brief **before** it works — as four
checkable lines you can veto in two seconds. No second model call, no extra
latency: the model sharpens its own request, with the full repo already in
context.

```
> /boost clean up the parser

Goal:   split parse() in src/parser.py into tokenize() + build_ast() → same public API
Done:   pytest tests/test_parser.py passes unchanged
Assume: "clean up" = readability, not speed — no algorithmic changes
Not:    the CLI wrapper in cli.py, even though it calls parse() directly

[…then it does the work]
```

Wrong assumption? You caught it on line 3 instead of after the diff.

## Install

```
/plugin marketplace add sernoxxx/prompt-boost
/plugin install prompt-boost
```

That gives you the `/boost` command and the automatic hook.

## Use

```
/boost <your request>          # default: the four-line brief
/boost lite <your request>     # Goal line only — small, clear tasks
/boost ultra <your request>    # brief + 3-5 numbered steps + biggest risk
```

Leave the request empty and it sharpens your previous message instead.

### The four lines

| Line | What it pins down |
|------|-------------------|
| `Goal:`   | verb, object, file/area, and an artifact someone can point at |
| `Done:`   | the check that proves it — a command, a test, an observable behavior |
| `Assume:` | the gap it filled for you, so a wrong guess is visible up front |
| `Not:`    | adjacent work it is deliberately leaving out — the scope fence |

Lines with nothing to say are dropped. The point is a brief you can scan, not a
form to fill in.

### The automatic hook

The plugin also installs a `UserPromptSubmit` hook that applies the same
sharpening to **every** prompt, so you don't have to remember to type `/boost`.
It stays out of the way for anything that isn't a work request: slash commands,
questions, `ok` / `thanks` / `stop`, and one- or two-word replies.

Don't want it? `/plugin` → disable, or install by hand (below) and skip the hook.

## Manual install

Copy the two files, no plugin system involved:

```sh
git clone https://github.com/sernoxxx/prompt-boost
cp prompt-boost/commands/boost.md ~/.claude/commands/
cp prompt-boost/hooks/prompt_boost.py ~/.claude/hooks/
```

The command works immediately. For the hook, add this to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/hooks/prompt_boost.py\"" }] }
    ]
  }
}
```

Check the hook's filter logic with `python3 prompt_boost.py --selftest`.

## Why this and not a "prompt improver"

Prompt improvers rewrite your words before the model sees the repo — they guess
at the same ambiguity you did, just more verbosely. This runs *inside* the
session: by the time it writes `Goal:`, it can open the file and check which
`parse()` you meant. Ambiguity gets resolved against the code, not against a
thesaurus.

Works with any language — it sharpens in whatever language you write in.

## License

MIT
