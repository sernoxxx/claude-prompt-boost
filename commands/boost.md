---
description: Pick how your prompt gets rewritten before you send it
allowed-tools: Bash(python3:*)
---

!`python3 ~/.claude/hooks/prompt_boost.py --cmd`

Do exactly what the block above says, starting with its first instruction, and
nothing beyond it.

If the block above is an error or the unexecuted command line rather than its
output, run the same command with Bash first - swapping the path for
$CLAUDE_PLUGIN_ROOT/hooks/prompt_boost.py if this is installed as a plugin -
and then follow what it prints.
