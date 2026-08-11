# prompt-boost

Most bad agent output starts with a bad brief. You type *"clean up the parser"*,
the model picks one of five readings, and you find out which one after it has
rewritten a file you liked.

`prompt-boost` sharpens the request before the model acts on it. That is the
whole feature. It shapes how your request is read and nothing else — it says
nothing about tone, format, length, verbosity or how to work. Your model
answers exactly as it always would, just to a better question.

```
> make the dashboard better

  ↓ rewritten before Claude sees it

  Improve the dashboard in ops/dashboard: tighten spacing and typography in the
  existing views without changing their data sources or layout structure.
  Assumption: "better" means visual polish, not new features.
```

## Runs on your subscription — no API key

The rewrite is a real model call, but it goes through the `claude` CLI you
already have, on the login you already have. No key, no separate billing. It
adds about 7 seconds to a prompt.

The rewriter runs in a config dir of its own (`~/.claude/boost-child`), so your
session hooks do not fire inside it — with them loaded a child session blocks on
a permission prompt and takes 40 seconds instead of 7.

Two other settings for `model`:

- `"self"` — no separate call and no wait at all: the model that is already
  answering restates the request itself.
- an Anthropic model id like `"claude-haiku-4-5"` — goes through the API
  instead, if you have `ANTHROPIC_API_KEY` set. Faster, billed per token.

If the rewrite fails or times out, `self` takes over. Nothing breaks either way.

**Sonnet is the default rewriter, not Haiku.** Haiku is faster but keeps
answering the request or asking clarifying questions instead of rewriting it —
"rewrite this without answering it" turns out to need the bigger model.

## Install

```
/plugin marketplace add sernoxxx/prompt-boost
/plugin install prompt-boost
```

That gives you the `/boost` command and the hook that runs on every prompt.

## Use

```
/boost            arrow-key picker for strength, kind and model
/boost ultra      set the strength straight (off | lite | full | ultra)
/boost status     show the current settings and whether the key is set
```

The choice is saved and applies to every prompt from then on.

## Settings

Everything lives in `~/.claude/boost.json`, read fresh on every prompt:

```json
{
  "level": "full",
  "mode": "rewrite",
  "style": "",
  "model": "sonnet"
}
```

| Key | Values | What it does |
|---|---|---|
| `level` | `off` `lite` `full` `ultra` | How far to push it. `lite` changes as little as possible; `full` marks filled gaps as assumptions; `ultra` adds the biggest risk in the request. |
| `mode` | `rewrite` `brief` `context` | What the rewrite turns into — see below. |
| `style` | free text | Extra steering for the rewriter, e.g. `"prefer the smallest change that works"`. |
| `model` | `sonnet` `haiku` `opus` `self`, or an API model id | Who rewrites. CLI aliases run on your subscription; `self` skips the call entirely. |
| `timeout` | seconds (default 25) | Past this, `self` takes over. Keep the hook timeout in `settings.json` above it. |

`/boost` covers `level`, `mode` and `model`; `style` and `timeout` are edited in
the file.

### The three kinds

| Mode | Your request becomes |
|---|---|
| `rewrite` | A precise request naming the target and the artifact that should exist afterwards |
| `brief` | `Goal:` / `Done:` / `Assume:` / `Not:` — what to do, the check that proves it, the gap it filled, the scope fence |
| `context` | The same request with the implicit parts spelled out |

## What it does not do

It never says anything about how the answer should come out — not terse, not
"skip the preamble", not "print this first". Every word the hook emits is about
reading the request. That is the whole difference from a prompt that tells your
model how to behave.

## The hook

The plugin installs a `UserPromptSubmit` hook so you never have to remember to
type anything. It skips what has nothing to sharpen: slash commands, one-liners,
questions, and acknowledgements like *"ok"* or *"thanks"*.

```
python3 hooks/prompt_boost.py --selftest
```

Turn it off with `/boost off`; the command still works to turn it back on.

## License

MIT
