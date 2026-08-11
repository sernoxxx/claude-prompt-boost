# prompt-boost

Most bad agent output starts with a bad brief. You type *"clean up the parser"*,
the model picks one of five readings, and you find out which one after it has
rewritten a file you liked.

`prompt-boost` sharpens the request before you send it. That is the whole
feature. It shapes how your request is read and nothing else — it says nothing
about tone, format, length, verbosity or how to work. Your model answers exactly
as it always would, just to a better question.

```
> make the dashboard better
                                    ↓ rewritten, session cleared

> Improve the dashboard in ops/dashboard: tighten spacing and typography in the
  existing views without changing their data sources or layout structure.
  Assumption: "better" means visual polish, not new features.▌
```

The rewrite is **not sent**. It is put back in your input box, in a cleared
session, and waits there — read it, edit it, press enter. The prompt the model
gets is the one you saw.

## Runs on your subscription — no API key

The rewrite is a real model call, but it goes through the `claude` CLI you
already have, on the login you already have. No key, no separate billing. It
adds about 8 seconds before your prompt comes back sharpened.

The rewriter runs in a config dir of its own (`~/.claude/boost-child`), so your
session hooks do not fire inside it — with them loaded a child session blocks on
a permission prompt and takes 40 seconds instead of 8.

Set `model` to an Anthropic model id and it goes through the API instead, if you
have `ANTHROPIC_API_KEY` set: faster, billed per token. If the rewrite fails or
times out, your original prompt goes through untouched. Nothing breaks either
way.

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
/boost      the picker: strength, kind, rewriter
```

That is the only way in. There is no `/boost ultra`, no keyword in front of your
prompt, no setting to find in Claude's own config — one command, three
arrow-key questions, saved and applied to every prompt from then on. Turn it off
in the same picker (`Strength → off`).

## Settings

The picker writes `~/.claude/boost.json`, read fresh on every prompt:

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
| `mode` | `rewrite` `brief` `context` `mini` | What the rewrite turns into — see below. |
| `style` | free text | Extra steering for the rewriter, e.g. `"prefer the smallest change that works"`. |
| `model` | `sonnet` `haiku` `opus`, or an API model id | Who rewrites. CLI aliases run on your subscription. |
| `timeout` | seconds (default 25) | Past this, your original prompt goes through. Keep the hook timeout in `settings.json` above it. |

`/boost` covers `level`, `mode` and `model`; `style` and `timeout` are edited in
the file.

### The four kinds

| Mode | Your request becomes |
|---|---|
| `rewrite` | A precise request naming the target and the artifact that should exist afterwards |
| `brief` | `Goal:` / `Done:` / `Assume:` / `Not:` — what to do, the check that proves it, the gap it filled, the scope fence |
| `context` | The same request with the implicit parts spelled out |
| `mini` | The same request, only with grammar and sentence structure cleaned up — nothing added, no gaps filled (`level` is ignored) |

## What it does not do

It never says anything about how the answer should come out — not terse, not
"skip the preamble", not "print this first". Every word it emits is about
reading the request. That is the whole difference from a prompt that tells your
model how to behave.

## The hook

The plugin installs a `UserPromptSubmit` hook so you never have to remember to
type anything. It skips what has nothing to sharpen: slash commands, one-liners,
questions, and acknowledgements like *"ok"* or *"thanks"*.

For everything else it blocks the prompt, clears the session and hands the
rewrite to your input box the only way a terminal accepts text from outside: as
the same key events you would have typed, sent to the window in front. That part
is Windows/WSL only — anywhere else the rewrite is passed to the model inline
instead, the way it worked before.

```
python3 hooks/prompt_boost.py --selftest
```

## License

MIT
