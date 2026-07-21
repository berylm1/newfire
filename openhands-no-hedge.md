---
name: nss_no_hedge
type: repo
version: 1.1.0
agent: CodeActAgent
---
# Output discipline + anti-loop rules (NewFire NSS)

## Tool-call discipline

Use OpenAI native function/tool calls only. Never emit pseudo-XML formats like
`<COMMANDS>`, `<BASH_COMMAND>`, `<TASK_COMPLETION>`, `<MAGIC_METHODS>`,
`<PERSISTENT_STATE>`, or `<RESPONSE_TO_USER>`. OpenHands does not parse those.
The only valid ways to act are real tool calls: `execute_bash`,
`str_replace_editor`, `think`, `browser`, `execute_ipython_cell`, or `finish`.

## When you finish

Call the `finish` tool. Do not write `TASK COMPLETE` as plain text and stop;
that is a chat message, not a finish action. The agent only terminates cleanly
when `finish` is invoked.

If a step failed and you cannot recover: call `finish` with a brief reason in
the message field. Do not loop hoping a different prompt will fix it.

## Anti-loop rules (avoid getting killed by the stuck detector)

1. **Do not repeat identical commands.** If you ran `ls /workspace` and got
   output, do not run it again. The output is in your history; reread it.
2. **If a command failed twice, change approach completely.** Do not retry
   the same `str_replace_editor` invocation with whitespace tweaks. Use a
   different tool (e.g., `execute_bash` with `cat > file <<EOF`) or rewrite
   the call from scratch.
3. **If `fetch` returns empty or errors twice on a topic**, give up on
   research and proceed using your training-data knowledge. State what you
   are assuming, then continue.
4. **Cap repeated tool retries at 3.** After 3 unsuccessful attempts to fix
   the same problem, write a one-paragraph status with the blocker and call
   `finish`.

## Verification before claiming done

Before calling `finish`, confirm in your action history that:
- Every numbered step the user listed has either run successfully or been
  explicitly skipped with reason.
- Any tests you wrote actually passed (you ran them and saw `passed`).
- Any files you claim to have written exist (you ran `ls` or `cat`).

## Forbidden phrasings

Never end a response with:
- "I believe that the task was completed partially"
- "the task may be incomplete"
- "I think I have completed"
- "It seems the task is partially done"

State results directly. Use the `finish` tool when done.
