# Discovery Agent Design

## The Problem

You have a phone number and a goal: find the fax number for submitting Remicade prior authorizations for commercial plans. You don't know what's on the other end — could be an IVR tree, a live agent, a voicemail box, or a disconnected line. And phone systems are adversarial by design: payers optimize for deflection, not resolution.

The interesting problems aren't the mechanics of making calls. They're the judgment calls: how do you know you've reached the right place? How do you recognize a dead end before wasting 40 minutes on hold? And how do you know when you have complete information vs. when you're missing something critical?

## Exploration Strategy

At each IVR menu, the agent scores options by semantic similarity to the goal. "For prior authorization, press 2" scores high. "For claims, press 3" scores low. Take the highest-scoring option first. If it dead-ends, backtrack to the last decision point and try the next-best option.

This is goal-directed depth-first, not exhaustive mapping. With 40-minute hold times, exploring irrelevant branches (claims, eligibility, member services) wastes real time. Each failed path still provides signal: "claims department doesn't handle PA" narrows future searches.

## Knowing When You've Reached the Right Place

A rep might say "I can help you with that" but only handle status checks, not submission requirements. The IVR might say "for prior authorizations, press 3" but route to a Medicare-only department.

Before asking the target question, the agent verifies: Can this department accept new PA submissions (not just status checks)? Do they handle infusion drugs (not retail pharmacy)? Do they handle commercial plans (not Medicare)?

If any verification fails, it's the wrong place — even if it sounds right. Backtrack and try a different path.

One failure mode from the reconciliation pipeline applies directly here: the LLM hallucinated phone hours as "M-F 8am-5pm EST" for every payer because that's what PA departments "typically" look like. A phone discovery agent faces the same risk. If it can't reach anyone at 5:30pm, it shouldn't infer the department closed at 5. It should only record hours when explicitly stated by an IVR or a rep. The rule: if you didn't hear it, don't write it down.

## Recognizing Dead Ends

The agent maintains a stack of decision points. When it hits a dead end, it pops back and tries the next branch.

- **Voicemail** (beep + "leave a message") — hang up, try alternate number
- **Disconnected** ("not in service") — remove from active number list
- **Wrong department** ("let me transfer you") — log what this department handles, follow the transfer
- **Circular transfer** (same hold music twice) — ask for supervisor or direct line
- **Permanent hold** (45+ min, no progress) — drop, retry off-peak hours

## Multiple Phone Numbers

A payer might have five numbers floating around: main provider line, dedicated PA line, pharmacy line, a number from an old PDF, a number a rep mentioned last month.

The agent calls each and classifies based on the first 60 seconds. "For prior authorization" is high priority. "For members, press 1" is probably wrong. After classification, rank by specificity (infusion PA line > general PA > provider services) and freshness (number from last week's denial > number from 2-year-old manual).

We saw this pattern in the reconciliation pipeline: Aetna's old fax number was still in the provider manual months after decommissioning. The pipeline detected this through supersession — matching current values against deprecated `*_old` fields. Phone trees change the same way. An IVR option that reached PA last month might route to claims after a system update. The agent needs the same logic: detect when a previously-working path reaches a different destination, mark the old path as invalid, and map the new one.

## Knowing When Information Is Complete

The agent got a fax number. Is it done? What if there's also a portal option that's faster? What if the form version changed last month?

Define a target schema upfront: submission method (required), fax/portal details (required), PA form version (recommended), turnaround time (recommended), required documents (recommended). After each call, map what you learned to the schema and check completeness.

The tricky part is capturing nuance. The IVR might say "decisions within 5 business days" but the rep says "honestly, we're running behind, more like 10-12 days." We built the reconciliation pipeline to preserve both `stated_policy` and `operational_reality` for exactly this reason. The agent should capture both. The stated policy is what the payer will hold you to; the operational reality is what ops needs to plan around.

## Learning Across Calls

Every call teaches the agent something. The system maintains a knowledge graph per payer: best PA number, IVR path to reach PA department, average hold time by day/time, known dead ends, and rep notes ("ask for medical management, not specialty pharmacy").

On each subsequent call, compare expected vs. actual. If the IVR menu changed, re-map the affected subtree. If a fax number differs from cached, flag for verification. If a rep mentions "system migration," invalidate cached data and re-explore.

The first call to a new payer might take an hour. The tenth call takes 5 minutes because the agent already knows the path. That's the value — not just navigating phone trees, but building institutional knowledge that compounds.

## Open Questions

- **Hold time strategy**: wait out a 40-minute hold, or hang up and try off-peak hours? Need data on success rate vs. time spent.
- **Rep variability**: how much do answers vary between reps? Should critical info be verified with a second call?
- **Change detection frequency**: how often should the agent re-verify known-good paths? Weekly? Monthly? Event-triggered by denial letters citing new policies?
