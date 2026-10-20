"""The three agents, on Pydantic AI. TODO 1 to 5.

This is the week the hand-rolled loop of weeks 1 to 4 gives way to a
framework. Read the week 4 `agent.py` next to this file: the loop, the
message list, the tool dispatch, and the schema envelope are all gone. What
is left is the part that was always the design.

Nothing underneath has changed. Pydantic AI is making the same calls to the
same endpoint in the same wire format. That is why you wrote the loop first.
"""

from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from repo import Work, apply_fix, diff_summary, run_tests

from project.models import LARGE, pydantic_ai_model

# Prima era qualcosa tipo 'ollama:qwen2.5:7b'
MODEL = 'openai:minimax/minimax-m3.1-flash:free'

# --------------------------------------------------------------------------
# TODO 1. The plan schema, and a warning about its shape.
# --------------------------------------------------------------------------
#
# The obvious schema for a plan is a list of structured steps:
#
#     class Step(BaseModel):
#         tool: Literal[...]
#         argument: str
#         why: str
#
# It fails on this model, every time, with "Exceeded maximum output
# retries". A flat list of strings works. That is measured, not folklore.


class Plan(BaseModel):
    """TODO 1. Three fields: a goal, the steps, and the file you suspect."""

    goal: str
    
    # TODO 1a: steps. Flat. 
    steps: list[str]
    
    # TODO 1b: suspect_file. The file most likely to contain the bug.
    suspect_file: str


planner = Agent(MODEL, output_type=Plan, retries=3,
                system_prompt=(
    "You plan a small change to a Python repository. "
    "You cannot run or edit anything: you only produce a plan that a person "
    "will read before anything runs. Deliver the plan by calling the "
    "final_result tool.\n"
    "Keep it to between two and six steps. Name the file you suspect."))


# --------------------------------------------------------------------------
# TODO 2. Validating the plan, for free, before anything runs.
# --------------------------------------------------------------------------

KNOWN_FILES = {"booking.py", "discounts.py", "pricing.py", "report.py"}


def validate_plan(plan: Plan) -> tuple[bool, list[str]]:
    """TODO 2. Four free checks. No model, no cost, run before anything else."""
    problems = []

    # 1. Il numero di step è compreso tra 2 e 6?
    if not (2 <= len(plan.steps) <= 6):
        problems.append(f"Il piano ha {len(plan.steps)} step, deve averne tra 2 e 6.")

    # 2. Il file sospettato esiste nel repository?
    if plan.suspect_file not in KNOWN_FILES:
        problems.append(f"Il file sospetto '{plan.suspect_file}' non esiste in KNOWN_FILES.")

    # 3. Almeno uno step menziona l'esecuzione dei test?
    has_verification = any("test" in step.lower() for step in plan.steps)
    if not has_verification:
        problems.append("Nessuno step menziona l'esecuzione o la verifica tramite i test.")

    # 4. Nessuno step deve proporre di modificare i test (cerchiamo verbi pericolosi associati alla parola test)
    for step in plan.steps:
        s_lower = step.lower()
        if "test" in s_lower and any(verb in s_lower for verb in ["edit", "change", "modify", "update", "rewrite"]):
            problems.append(f"Uno step propone di modificare i test, cosa vietata: '{step}'")

    # Se la lista dei problemi è vuota (lunghezza 0), il piano è valido (True)
    is_ok = len(problems) == 0
    
    return is_ok, problems


# --------------------------------------------------------------------------
# TODO 3. The fix, as a proposal rather than an edit.
# --------------------------------------------------------------------------
#
# The executor does not edit the file. It proposes exactly one line change
# and `repo.apply_fix` decides whether to apply it.
#
# That is a deliberate narrowing and it is the difference between a session
# that works and one that does not. Given free-form editing tools, this model
# thrashes: measured at 32 and 38 tool calls, three to four minutes, and zero
# successful fixes in three attempts. Given one structured proposal, it is
# correct three times in four.
#
# The engineering point generalizes past this lab. The narrower the action
# your agent can take, the more reliably it takes it, and the easier it is to
# check before it happens. "Give the agent a shell" is the widest possible
# action and it is why coding agents are hard.

from pydantic import BaseModel, Field

class Fix(BaseModel):
    """TODO 3. One proposed line change.

    Four fields: the path, the exact line to replace, the corrected line,
    and why. The description you give `old_line` matters more than the type
    does, because `repo.apply_fix` refuses the edit unless that string
    appears in the file character for character.
    """

    # TODO 3a: path, old_line, new_line, why
    path: str
    old_line: str = Field(
        description="The exact wrong line to replace, copied character for character from the original file. No modifications or missing spaces."
    )
    new_line: str
    why: str


fixer = Agent(MODEL, output_type=Fix, retries=3,
              system_prompt=(
    "You propose exactly ONE line change that makes a failing test pass.\n"
    "You are given the whole file. Return the single wrong line, copied "
    "character for character, and the corrected version of it.\n"
    "Change the logic that is wrong. Do not change a constant to compensate "
    "for a wrong comparison, and never propose a change to a test."))


# --------------------------------------------------------------------------
# TODO 4. The baseline, for comparison. Given complete: read it.
# --------------------------------------------------------------------------

class Work_(BaseModel):
    root_str: str
    model_config = {"frozen": True}


baseline = Agent(MODEL, system_prompt=(
    "You fix a bug in a small Python repository using the tools provided.\n"
    "run_tests to see the failure, read_file to look at the source, "
    "replace_line to change one line, run_tests again to confirm.\n"
    "Never edit anything under tests/. Stop as soon as the tests pass."))


@baseline.tool
def list_files(ctx: RunContext[Work]) -> list[str]:
    """List the Python files in the repository."""
    return ctx.deps.files()


@baseline.tool
def read_file(ctx: RunContext[Work], path: str) -> str:
    """Read one file, by a path relative to the repository root."""
    return ctx.deps.read(path)


@baseline.tool
def replace_line(ctx: RunContext[Work], path: str, old_line: str,
                 new_line: str) -> str:
    """Replace one exact line. The old line must appear exactly once."""
    return apply_fix(ctx.deps, path, old_line, new_line)


@baseline.tool
def run_the_tests(ctx: RunContext[Work]) -> str:
    """Run the test suite and return its output."""
    return run_tests(ctx.deps).output


# --------------------------------------------------------------------------
# TODO 5. The reviewer, which is the second agent.
# --------------------------------------------------------------------------

class Verdict(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(..., max_length=500)


# TODO 5. Write the reviewer's instructions.
#
# It is given the diff and the failing test output, and nothing else. Decide
# what it should reject. At least one of the things it must catch is a change
# that makes the failing test pass while being wrong anyway, and the fixer
# really does propose one sometimes.
#
# Do NOT give it the fixer's reasoning. If it inherits the reasoning it
# inherits the mistake, and the second opinion stops being a second opinion.
reviewer = Agent(
    MODEL,
    output_type=Verdict,
    system_prompt=(
        "You review proposed code changes against failing test output.\n"
        "Approve only if the change directly addresses the failure without "
        "breaking specifications.\n"
        "CRITICAL: Keep your 'reason' strictly under 150 characters, exactly one short sentence."
    ),
)


# --------------------------------------------------------------------------
# What the reviewer is NOT given, and why it matters
# --------------------------------------------------------------------------
#
# It does not see the fixer's reasoning. It sees the artifact and the test
# output. If it inherited the reasoning it would inherit the mistake, and the
# second opinion would stop being a second opinion. That is the mechanism
# behind the critic pattern and it is the thing worth demonstrating today.


async def propose(work: Work, task: str, use_plan: bool) -> dict:
    """One attempt: optionally plan, then propose a fix, then verify."""
    out: dict = {"plan": None, "plan_ok": None, "plan_problems": [],
                 "fix": None, "applied": None, "tokens": 0}
    t0 = time.perf_counter()

    context = ""
    if use_plan:
        r = await planner.run(task)
        out["plan"] = r.output
        out["tokens"] += r.usage.total_tokens or 0
        ok, problems = validate_plan(r.output)
        out["plan_ok"], out["plan_problems"] = ok, problems
        context = (f"A plan has already been made. Suspect file: "
                   f"{r.output.suspect_file}. Goal: {r.output.goal}\n")
        source_name = (r.output.suspect_file if r.output.suspect_file
                       in KNOWN_FILES else "discounts.py")
    else:
        source_name = "discounts.py"

    failing = run_tests(work).output
    source = work.read(source_name)
    prompt = (f"{context}File {source_name}:\n{source}\n\n"
              f"Failing test output:\n{failing}\n\n{task}")
    r = await fixer.run(prompt)
    out["fix"] = r.output
    out["tokens"] += r.usage.total_tokens or 0
    out["seconds"] = time.perf_counter() - t0
    return out
