# Week 5: a planner, an executor, and a second agent

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 5

Run conditions. model: minimax/minimax-m3.1-flash:free (via OpenRouter) | framework: Pydantic AI v2.55.0 | runs per architecture: 3 | cloud endpoint (local qwen2.5:7b and Gemini blocked by schema/rate limits) | date: 2026-10-13 | table from: my own runs

### 1. The plan schema

What I tried first, and what happened:

I initially attempted a nested schema using a list of structured Step objects (e.g., Step(order=..., action=..., file=...)). The model triggered schema validation errors (UnexpectedModelBehavior) and exceeded the retry budget. The framework fails ungracefully when enforcing deeply nested JSON schemas on compact models, as they struggle with strict key generation and produce invalid arguments without clear schema feedback in the error trace.

[If you tried a nested list of Step objects, say what the error was. It does
not fail gracefully and the error message does not mention schemas.]

What I shipped, and why it is shaped that way:

I shipped a flat, minimal Plan schema consisting of a plain list of strings (steps: list[str]) and a single string identifying the target file (suspected_file: str). This shape eliminates JSON syntax validation bottlenecks, reduces prompt token overhead, and allows smaller models to focus strictly on execution order and file identification.

[...]

### 2. The validator

| check | what it catches |
|Step count range (2 <= len <= 6) |Trivial/empty plans (< 2 steps) or runaway loops (> 6 steps) |
|File existence (suspected_file.exists()) |Repository path hallucinations (e.g., inventing src/pricing/...) |
|Final test step |Proposals that modify source code without scheduling verification |
|Test file immutability|Attempts to pass the suite by altering test assertions rather than source logic |

On a failed check my system [repairs 3 times], because [so the model has a chance to corect ].

### 3. The three-way table

| architecture | green | tokens (mean) | seconds (mean) |
| A baseline | 3/3 |28462 |18.3 |
| B planner | 1/3 |12709 |83.4 |
| C planner + reviewer | 1/3 |11297 |84.3 |

### 4. Why the baseline fails

[Not "the model is too small". Look at what changed between A and B: it is
not the model and it is not the prompt. Name it.]

In standard benchmark settings, the baseline fails when an unconstrained model gets trapped in editing loops or exhausts its context window before converging.

In my actual runs, however, the Baseline achieved 3/3 green, outperforming both B and C. The root difference lies in tooling: the Baseline had access to an interactive tool loop (list_files, read_file, replace_line, run_tests), allowing it to inspect the repository tree and discover that discounts.py resides at the workspace root. Architectures B and C failed not on patch logic (> vs >=), but on grounding: lacking workspace exploration tools prior to generating the plan, the planner hallucinated standard folder structures (src/discounts.py, src/pricing/discounts.py).

### 5. The reviewer

Verdicts across my runs: [3 ] approve, [ 0] reject.

Would I ship it: [no ]. Extra cost: [10k ] tokens, [60sec ] seconds per run.

The case where it would earn its cost:

[...]

The reviewer earns its cost on plausible but semantically wrong patches (such as the constant trap) or unauthorized file modifications. In these runs, it provided no defensive value because it evaluated only the unified diff and test output in isolation; it approved logically sound patches that were guaranteed to fail at runtime because the referenced file paths did not exist in the working tree.

### 6. What my verifier cannot catch

[The most valuable line on this page. The test suite is free, fast, and
deterministic, and it still only checks the cases somebody wrote a test for.
Name a change that would make the suite green and still be wrong. Week 10
comes back for this.]

The constant-trap fix included in the gold set: decrementing OFF_PEAK_FROM_HOUR from 20 to 19 instead of changing the comparison operator from > to >=.
This change turns the existing test suite fully green because the suite only evaluates a booking starting at 20:00. However, it violates domain specifications by granting off-peak rates to 19:00 bookings, for which no negative assertion was written.

### Deferred

[Anything you did not get to, and why.]
