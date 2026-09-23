# Week 2: a structured-output extractor, measured

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 2

**Run conditions.** model: [ qwen3:4b-instruct ] | temperature: 0.0 | prompt version: [ few-shot v1] |
served locally | date: [2026-09-22] | scored on: [my own
machine]

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: `null`
- due_date, when the message states only a relative expression: converted to absolute ISO 8601 string format (YYYY-MM-DD).
- quote, and what "verbatim" means in my scorer: exact substring match. The extracted string must exist completely and exactly within the original document text.
- what my scorer does with a record that failed validation: it catches the exception, counts it as an invalid record (invalid +1), and marks all fields for that document as failed (0 score).

[One sentence on why the last one matters. A scorer that skips the records
it could not parse reports a number that improves as the model gets worse.]
So that i know when and why an error accured, so that the machine cannot "lie"

### 2. Zero-shot, per field

| field | correct | of |
| category |9 | 10 |
| urgency |10 | 10 |
| due_date |8 | 10 |
| quote |10 | 10 |
| invalid records |0 | 10 |

My prediction, written before block 3: examples will help most on [ due date]
because [ the examples will make clear that in case of missing date he should not guess].

### 3. Few-shot

Examples chosen, and the job each one does:

| example | why it is in the block | field it should move |
| EX-01 (EN) | Demonstrates returning `null` when no date is present, and clarifies the "access" boundary. | due_date, category |
| EX-02 (FR) | Multilingual support (French), demonstrates a "facilities" issue, and reinforces the `null` date. | category |
| EX-03 (DE) | Multilingual support (German), demonstrates absolute date conversion, and strict verbatim quote extraction. | quote, due_date |

| field | zero-shot | few-shot | move |
| category | 9/10 | 8/10 | -1 |
| urgency | 10/10 | 9/10 | -1 |
| due_date | 8/10 | 8/10 | +0 |
| quote | 10/10 | 10/10 | +0 |

### 4. What got worse

[Name the field, if any, and diagnose it. If nothing got worse, say so and
say how you checked. Then look at the failure lines rather than the counts,
and say whether any error disappeared or merely changed shape. A wrong label
that became a different wrong label has not been fixed.]

yes, category and urgency got wroste, probably the extremism of the examples made the model “confuse” even more then before

### 5. What the examples cost

- extra input tokens per call: [260 ]
- per thousand calls: [260000 ]
- estimated euros per thousand calls on the small tier: [0.15 ], against the
  price list dated [september 2026 ]. Estimate, not a measurement.

### 6. Ship it or not

[Which variant, on what evidence, and what would change your mind. Ten
records is not enough to be confident and saying so is worth more than
claiming a win. If your answer is "keep one example and drop the rest", say
which one and why.]
I would not ship it, the example i put just confused the model, so either i have to make better examples or the order/number of them were the real problem, in any case this particular input is not rigth

### Sensitivity variant

Variant assigned: [ reordered ]. What I changed: [change the order of examples ]. What moved: [ +1 urgency].

[If nothing moved, say so. A knob that changes nothing measurable is a real
result, and it tells the room which knobs are worth arguing about.]

### The gold set

Ten cases written to `artifacts/goldset.json`, tagged by language.

One thing my scorer cannot currently detect:

[This is the most valuable line on the page. An example: "our scorer cannot
tell a correctly formatted date that is simply the wrong date from a
correctly extracted one, because it only compares strings."]
Our scorer cannot tell if an extracted `quote` is semantically meaningful or useful for a human operator; it only validates if it is there.

### Deferred

[Anything you did not get to, and why.]
why my examples did not improve the model anwesore? what could i have done better?
