# Keymaker Sales

The sales desk of **Keymaker**, an agency that sets up automation on Trinity for other
companies. One of the Keymaker agency starter templates, built in public during the
[Agent-Native Agency workshop](https://www.ability.ai/trinity/workshops/agent-native-agency-workshop).

It runs a deal from first call to signature on a real pipeline with fixed stages, lets several
people work their own deals at once, drafts every email for a human to send, and asks the
operator before a price moves off the price list.

## Install

On any Trinity instance: **Library → Agents → Keymaker Sales → Create**. No credentials needed.

Or from a manifest / the API: `template: github:Abilityai/keymaker-sales`.

## What it runs on

| Credentials | Pipeline backend |
|---|---|
| none (default) | `pipeline/deals.yaml` in the agent's workspace, with three sample deals |
| `FIBERY_HOST` + `FIBERY_API_TOKEN` | your Fibery CRM (`CRM/Opportunities`), same stage names |

`scripts/crm.py` is the only path to the pipeline on either backend. Every write prints the
change and needs `--confirm`.

## Playbooks

- `/deal` - open a deal, review the pipeline, move a stage on evidence
- `/draft-outreach` - an email as a file in `drafts/`, sent by the owner

## Make it yours

1. `operators.yaml` - who may operate it and what they see
2. `pricing.md` - your offers; the only source of prices
3. `pipeline/deals.yaml` - replace the sample deals, or set the Fibery credentials

## Licence

Apache 2.0.
