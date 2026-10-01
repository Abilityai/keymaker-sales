---
name: draft-outreach
description: Draft an email for a deal as a file in drafts/ that the deal owner sends under their own name. This agent never sends. Use for "draft the follow-up to X", "write the intro email for X", "cover note for the proposal".
argument-hint: "<company or slug> [--purpose intro|follow-up|proposal-cover]"
allowed-tools: [Read, Write, Bash, Glob, Grep, AskUserQuestion]
user-invocable: true
metadata:
  version: "0.1"
  created: 2026-10-01
  author: keymaker
---

# Draft outreach

## Rules

- Identify the operator (`operators.yaml`); work only on a deal they own (principal: any).
- Read the deal first: `python3 scripts/crm.py show <slug>`. The draft must reflect the notes,
  the stage, and the champion's name. Nothing invented.
- Prices only from `pricing.md`. Anything not there is written as `[NEEDS-PRICE-LIST]`.
- **Never send.** The output is a file. If the operator asks you to send it, say no and point at
  the file.

## Output

`drafts/<slug>-<purpose>-<YYYY-MM-DD>.md` with:

```
To: <champion email if known, else [EMAIL]>
Subject: <one line>

<body: under 150 words, one ask, no headings>

--
Sent by <owner name>, Keymaker
```

Then: append a note to the deal (`crm.py note <slug> --text "Draft <purpose> written: <file>"`,
with the operator's confirmation) and tell the operator the path.

## Purposes

- **intro**: after a first conversation or an inbound; propose the discovery call.
- **follow-up**: the deal has gone quiet (see `updated`); one specific reason to reply.
- **proposal-cover**: the proposal is ready; the email names the offer from `pricing.md` and
  the next step.
