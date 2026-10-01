---
name: deal
description: Open a deal, review the pipeline, or move a deal to the next stage. The spine of Keymaker Sales - every other playbook works on a deal this one knows about. Use for "start a deal with X", "what's in my pipeline", "move X to qualified", "what needs attention".
argument-hint: "[<company or slug>] [--review] [--move <stage>] [--owner <name>]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
user-invocable: true
metadata:
  version: "0.1"
  created: 2026-10-01
  author: keymaker
---

# Deal

## Rules

- **Identify the operator first.** Read `operators.yaml`. No entry: refuse and say who to ask.
  A `rep` sees only deals whose `owner` matches their `crm_user`; the `principal` sees all.
- **Never write without showing the change.** `scripts/crm.py` prints every write and refuses
  without `--confirm`. Show the operator the line, then re-run with `--confirm`.
- **Stages are fixed** (CLAUDE.md). A stage moves only when its entry condition is in the notes.

## Modes

| Mode | Trigger | What you do |
|------|---------|-------------|
| review | `--review` or "what's in my pipeline" | `python3 scripts/crm.py list --owner "<crm_user>"` (principal: no `--owner`). Show the table. For each deal, one line: the single next action and who owns it. Call out `STALLED` rows (14+ days) first. |
| open | a company with no deal yet | Slug it (`acme-corp`). Check `list --all` for a match first. `create <slug> --company ... --owner "<crm_user>"`, show, then `--confirm`. Then ask the three questions: who is the champion, what do they run today, when is the first call. Add them with `note`. |
| edit | "the value is now", "new champion", "reassign to" | `edit <slug> --value N / --champion / --owner`, with confirmation. A price off `pricing.md` needs the principal first (CLAUDE.md rule 2); a rep asks via `ask_operator` and waits. |
| move | `--move <stage>` or "move X to ..." | Read the deal (`show <slug>`). Check the entry condition for the target stage against the notes. If it is evidenced, `move` with the operator's confirmation. If not, say exactly what evidence is missing and do not move. |

## After a review

Record the numbers this desk owns (if `record_metrics` is available): `open_deals`,
`stalled_deals`. Otherwise print them at the end of the review.

## When a deal reaches Won

Write `drafts/<slug>-handoff.md` for Keymaker Delivery: client, what was sold, price from the
proposal, champion, first three things Delivery must do. Tell the operator it is there.
