---
description: Set how your prompt gets rewritten before Claude sees it
argument-hint: [off|lite|full|ultra|status]
allowed-tools: Bash(python3:*)
---

!`python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/hooks/prompt_boost.py" --cmd "$ARGUMENTS"`

Do exactly what the block above says, starting with its first instruction, and
nothing beyond it.

If the block above is still the unexecuted command line rather than its output,
run it with Bash first and then follow what it prints.
