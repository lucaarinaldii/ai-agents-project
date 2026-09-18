# Decisions

## Week 1

**Run conditions.** Everything below was produced on:

- machine: [make: HP, chip: Intel I5 7th gen, RAM: 16gb]
- model: [the model name, exactly as `ollama list` prints it: qwen2.5:7b]
- served by: Ollama, one request at a time, locally
- date: [2026-09-16]

Every number in this file is meaningless without those four lines, so they
are stated once here and referred to rather than repeated.

### 1. Machine and model set

I am running the [qwen2.5:7b / nomic-embed-text:latest / qwen3:4b-instruct] model set.

[If you could not run the optional models, say so and say what you will do
before week 9. This is a constraint on your project, not a failure, and
naming it now is worth more than discovering it in week 9.]

### 2. The first call

| | |
| finish reason | | stop
| prompt tokens | | 20
| completion tokens | | 3
| elapsed | | 33.98 S

One sentence on the finish reason: what my program would do differently if
it came back as a truncation rather than a normal stop.

The program (and us) would know that the reason for the stop is the number of token, while stop means that everything got smooth and no problem accourd

[...]

### 3. Variance

| cell | distinct (recording) | distinct (mine) | median latency |
| closed_short, t=0.0 | 1/12 | | |
| closed_short, t=1.0 | 1/12 | | |
| open_list, t=0.0 | 1/12 | | |
| open_list, t=1.0 | 11/12 | | |

Which cell still returns a single answer at temperature 1.0, and why that
one:
Closed Short T10, that is because the anwesore it's a single word anwesore and is constant, so even adding probability to the anwesore is alway the same

[...]

Which cells a test asserting exact string equality would pass on, and what
that tells me about testing this system:

all the tests with T00 and closed short T10, test tell us that conventional way of checking for anwesore are not effective if the temperature is higth enough (and the anwesore is not constant and not subjected to a rephrasing).
[...]

**The sentence that carries into week 10.** [One sentence about when you can
and cannot rely on repeating an output. Week 10 will ask you to find this
again. It should not say "the model is random", because your own table shows
otherwise in most cells.]

The model is not random, every time that he “thinks” the random part is just the last and most unconsequentil choosing of the wording.
Is repetable only in very specific condition (like low temperature or a constart and short anwesore)


### 4. The cold start

- cold call: [ 85.52 ] s
- warm call: [ 46.48 ] s
- ratio: [ 1.84 ]

What this implies for a system that uses more than one model, and what I
will do about it:

this implies that, for having better results, more then one model at the time needs to stay on the ram or vram, or at least a part big enougth to not cause this big delay (we will do this)
[...]

### 5. Cost, estimated

A 200-case golden set, at the token cost of my long case:

| | one run | nightly for the semester |
| small tier | | | 3,284.96 EUR for 1.000 calls
| large tier | | | 244,137.60 EUR for 1.000 calls

Estimates against the price list dated [date in `project/prices.py`], not
measurements. Running locally, my actual monetary cost was zero.

Which tier I would run nightly, which I would run before a release, and why
not the same one for both:

obviously the shorter one is faster and cheaper but before a push I would use the longer one because is more precise
[...]

### Deferred

[Anything you did not get to, and why. An explicit deferral with a reason is
engineering. Silence is not, and the project rubric can tell the
difference.]

