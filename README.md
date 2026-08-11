# prompt-boost

Most bad agent output starts with a bad brief. You type *"clean up the parser"*,
the model picks one of five readings, and you find out which one after it has
rewritten a file you liked.

`prompt-boost` rewrites the prompt before the model sees it. That is the whole
feature. A small model turns your request into a sharper version of the same
request, and that text is all the hook emits — no instructions about tone,
format, length or how to work. Your model answers exactly as it always would,
just to a better question.

```
> make the dashboard better

  ↓ rewritten before Claude sees it

  Improve the dashboard in ops/dashboard: tighten spacing and typography in the
  existing views without changing their data sources or layout structure.
  Assumption: "better" means visual polish, not new features.
```

## Requires an API key

The rewrite is a real model call, so it needs `ANTHROPIC_API_KEY` in the
environment. Put it in `~/.claude/settings.json`:

```json
{ "env": { "ANTHROPIC_API_KEY": "sk-ant-..." } }
```

Get one at [console.anthropic.com](https://console.anthropic.com/settings/keys).
It is billed per token and separate from a Claude subscription; on
`claude-haiku-4-5` a rewrite costs a fraction of a cent and adds about a second.

**Without a key the hook prints nothing at all** and your prompt reaches the
model exactly as you typed it. Nothing breaks, nothing is added — boost is
simply inactive.

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
  "model": "claude-haiku-4-5"
}
```

| Key | Values | What it does |
|---|---|---|
| `level` | `off` `lite` `full` `ultra` | How far to push it. `lite` changes as little as possible; `full` marks filled gaps as assumptions; `ultra` adds the biggest risk in the request. |
| `mode` | `rewrite` `brief` `context` | What the rewrite turns into — see below. |
| `style` | free text | Extra steering for the rewriter, e.g. `"prefer the smallest change that works"`. |
| `model` | an Anthropic model id | Who rewrites. `claude-haiku-4-5` is the cheap default. |
| `timeout` | seconds (default 12) | Past this the prompt is left alone. |

`/boost` covers `level`, `mode` and `model`; `style` and `timeout` are edited in
the file.

### The three kinds

| Mode | Your request becomes |
|---|---|
| `rewrite` | A precise request naming the target and the artifact that should exist afterwards |
| `brief` | `Goal:` / `Done:` / `Assume:` / `Not:` — what to do, the check that proves it, the gap it filled, the scope fence |
| `context` | The same request with the implicit parts spelled out |

## What it does not do

It never adds instructions for the answering model — not about being terse, not
about skipping preamble, not about printing anything. The hook's entire output
is your rewritten prompt inside a `<boosted-prompt>` tag. If the rewrite fails,
times out, or has no key, the output is empty.

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
