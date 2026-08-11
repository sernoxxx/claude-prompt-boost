# prompt-boost

Most bad agent output starts with a bad brief. You type *"clean up the parser"*,
the model picks one of five readings, and you find out which one after it has
rewritten a file you liked.

`prompt-boost` sharpens the **request** before the model acts on it. That is all
it does — it never touches how the answer is written. Your model's tone, format,
length and working style stay exactly as they were.

```
> /boost

  Strength   full · lite · ultra · off
  Kind       brief · rewrite · context
  Model      self · claude-haiku-4-5 · claude-sonnet-5
```

Pick with the arrow keys, or set it straight: `/boost ultra`, `/boost off`.
The choice is saved and applies to every prompt from then on.

## Install

```
/plugin marketplace add sernoxxx/prompt-boost
/plugin install prompt-boost
```

That gives you the `/boost` command and the hook that runs on every prompt.

## Settings

Everything lives in `~/.claude/boost.json`, read fresh on every prompt:

```json
{
  "level": "full",
  "mode": "brief",
  "style": "",
  "model": "self",
  "show": false
}
```

| Key | Values | What it does |
|---|---|---|
| `level` | `off` `lite` `full` `ultra` | How hard to sharpen. `lite` is one line; `ultra` adds the biggest risk in the request. |
| `mode` | `brief` `rewrite` `context` | What kind of sharpening — see below. |
| `style` | free text | Appended to the instruction, e.g. `"prefer the smallest change that works"`. |
| `model` | `self` or a model id | Who sharpens. `self` is the model already answering: no extra call, no added latency. |
| `show` | `false` `true` | `true` prints the sharpened reading before the answer. Off by default. |

`/boost` covers `level`, `mode` and `model`; `style` and `show` are edited in the
file.

### The three modes

| Mode | The request becomes |
|---|---|
| `brief` | `Goal:` / `Done:` / `Assume:` / `Not:` — verb, object, the check that proves it, the gap it filled, the scope fence |
| `rewrite` | One precise sentence naming the target and the artifact |
| `context` | What the request left implicit: the file or area it points at, and what would count as done |

### Using a separate model

With `model: "self"` nothing extra runs — the answering model just reads its own
request more carefully, with the whole repo already in context. That is the
default, and it costs nothing.

Set `model` to an Anthropic model id (`claude-haiku-4-5` is the cheap one) and
the prompt is rewritten through the API first. This needs `ANTHROPIC_API_KEY` in
the environment — you can set it in `~/.claude/settings.json`:

```json
{ "env": { "ANTHROPIC_API_KEY": "sk-ant-..." } }
```

Without a key, or if the call fails or times out, the prompt is left exactly as
you typed it and `self` takes over. A rewrite adds about a second per prompt.

## What it does not do

It does not tell the model to be terse, to skip preamble, to print a brief, or
to work in any particular way. Everything the hook emits is scoped to reading
your request. If you want the brief visible, that is `"show": true` — opt-in.

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
