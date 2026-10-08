# Week 3: a router in front of the extractor

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 3

**Run conditions.** classifier model: [qwen3:4b-instruct ] | answering model: [qwen3:4b-instruct ] |
temperature: 0.0 | served locally | date: [2026-09-29] | scored on: [the
recording / my own machine]

### 1. The five route definitions

| route | definition, one sentence, in terms of what the help desk must do |
| request | Something is broken, missing, or needed, and the help desk is
              expected to log it and act. This is the week 2 extractor's job. |
| info | A question about a service, a procedure, an opening time, or a
              form. The answer is information, not an action. |
| status | The sender is chasing something already reported. There may or
              may not be a reference number in the message. |
| complaint | The sender expresses dissatisfaction with the service itself,
              with how something was handled, or with how long it took. |
| other | Not help desk business: a message for another department, a
              request for advice the help desk cannot give, spam, or an
              instruction aimed at the system rather than at a person. |

My convention for the four ambiguous queries: INFO

[Two defensible conventions exist. Neither is discoverable from the data.
What matters is that yours was written down before you measured, not which
one you picked.]

Do my definitions match the ones in `queries.py`? [yes]

### 2. The policy layer

Before choosing a threshold, the confidence values I saw were: min [0.00 ],
max [1.00 ], [4 ] distinct values across 24 queries.

- confidence floor: [0.99 ], because [even when the anwesore were wrong the confidence was >0.9 ]
- evidence check: [send it to info], because [ so the program continue flowind and has another chance to come out correct (wrong anwesore is more constly) ]
- safe default: [info ], because that specialist [the definition was more fitting ]

How often each check fired: below_threshold [0 ], evidence_not_verbatim [ 1],
invalid_decision [2 ].

[If a check fired zero times, say what that tells you. A threshold that
never fires is either a very good classifier or a useless signal, and the
confidence distribution above tells you which.]

### 3. Route accuracy

| route | correct | of |
| request | 6 | 7 |
| info | 5 | 5 |
| status | 4 | 4 |
| complaint | 3 | 4 |
| other | 2 | 4 |

Overall 20/24. Excluding the four ambiguous: 17/20

Confusion pairs, with direction:

| gold | applied | count |
|other |info | 2|
|request | info | 1|
|complaint | info| 1|

The route carrying most of the error is [ info]. The fix is [a definition], because [ too long, it "steal" from the other routes ].

### 4. What routing cost

- monolith: [ 5405] tokens over 24 queries
- router: [17431 ] tokens over 24 queries
- the classifying call alone: [13237 ] tokens, which is [76 ] per cent of the
  routed total

I predicted that share would be [30/40 ] before measuring it.

[If the share surprised you, say why. The classifier's prompt carries every
route definition on every call, and the specialists carry only their own.]

i expected far less, from the theory i knew that it would have been expensive but i did not expect a >50% anwesore, the division is more presice but it cost far more (maybe shortening the definition would help)

### 5. What routing bought

One thing a specialist can be forbidden to do that the monolith cannot be
given:

[special instruction/restrictions]

Would I ship the router: [ yes ]. Evidence: [ it cougth the errors ]. What would change my mind: [ watching the anwesore of the monolite and if they are the same (we cannot know what the mololite was thinking) ].

### 6. Stretch variant

Variant assigned: Voting. Result: 20/24 routed correctly

[For model routing: report both models on accuracy, evidence verbatim, the
confidence range, and resident memory. If the smaller model won, say so
plainly and say what you think that means.]

[For voting: report the split-vote count at each temperature. If nothing
ever disagreed, that is the result. Say what it cost and what it bought.]

The voting system consumed a total of 43,879 tokens, of which the routing call alone accounted for 39,687 tokens (90 per cent of the total routed). This shows us that voting does not resolve uncertainty (as it produces exactly the same results as before the vote) and is therefore simply an unjustified waste of tokens.

### The gold set

artifacts/goldset.json now holds 34 cases: 10 from week 2 and 24 added
today, with the four ambiguous ones tagged.

### Deferred

[Anything you did not get to, and why.]
