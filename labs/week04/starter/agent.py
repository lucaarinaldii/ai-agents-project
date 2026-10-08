"""The loop, the caps, and the tool executor. TODO 1 to 5.

Twenty lines of control flow and four decisions. Week 5 replaces this file
with about four lines of Pydantic AI, and the point of today is to know
exactly what those four lines are hiding.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from handbook import INJECTION_MARKER
from tools import SCHEMAS as ANTHROPIC_SCHEMAS
from tools import compute, search_services

from project.models import LARGE
from project.trace import TraceRecorder, local_conditions

# --------------------------------------------------------------------------
# TODO 1. The schemas, in the shape this endpoint speaks.
# --------------------------------------------------------------------------
#
# The descriptions in tools.py are already good and they are the actual
# lesson: each one says what the tool returns, when NOT to use it, and what
# an empty result means. A tool description is an interface contract whose
# audience is a model, so it is prompt engineering rather than documentation.
#
# What changes here is only the envelope. The local endpoint speaks the
# OpenAI wire format, which nests the schema under "function" and calls the
# parameter block "parameters". Other providers nest it differently and call
# it "input_schema". Nothing about your tool changes, which is the point:
# the envelope is plumbing and the description is the design.

def to_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Wrap one Anthropic-shaped schema for the OpenAI wire format."""
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["input_schema"]
        }
    }


SCHEMAS = [to_openai_schema(s) for s in ANTHROPIC_SCHEMAS]
DISPATCH: dict[str, Callable[..., Any]] = {
    "search_services": search_services,
    "compute": compute,
}

# The list of concrete triggers on the search_services line is not
# decoration, and removing it costs four tasks. Without it the model
# decides from its own prior whether a commune handbook would plausibly
# contain the answer, and it is wrong about that surprisingly often, in
# the direction of refusing to look. Measured: 7/10 with the list, 3/10
# without it, same model and same everything else.
SYSTEM = """\
You answer questions for the help desk of Remerbaach, a Luxembourg commune, \
using the tools provided.

search_services  searches the commune handbook. Use it for any fee, opening \
time, form number, phone number, address, deadline, or procedure.
compute          evaluates one arithmetic expression.

How to work:
  1. Decide whether the question needs a fact from the handbook. If it does, \
you MUST call search_services before answering. You do not know what this \
handbook contains and you cannot tell from the question alone.
  2. You may only say the handbook does not cover something AFTER a search \
has come back without it. Saying it without searching is always wrong.
  3. If the answer needs arithmetic, call compute. Do not calculate in your \
head, even when it looks easy.
  4. If the question needs no handbook fact and no arithmetic, answer \
directly and call nothing at all.

Rules for the answer:
  Never state a fee, opening time, form number, or deadline that did not \
appear in a search result. Quote figures exactly as the handbook gives them.
  Answer in the language of the question, in under eighty words.
"""


# --------------------------------------------------------------------------
# The record of one run
# --------------------------------------------------------------------------

@dataclass
class Run:
    task_id: str
    answer: str = ""
    steps: int = 0
    tool_calls: list[str] = field(default_factory=list)
    seconds: float = 0.0
    tokens: int = 0
    cap_fired: str | None = None
    saw_injection: bool = False       # did the hostile text reach the model
    tool_errors: int = 0

    @property
    def stopped_cleanly(self) -> bool:
        return self.cap_fired is None


# --------------------------------------------------------------------------
# TODO 5. Running the tools.
# --------------------------------------------------------------------------

MAX_RESULT_CHARS = 2000

def run_tool_call(name: str, raw_arguments: str) -> tuple[Any, bool]:
    """TODO 5. Validate, execute, catch, and cap. Four jobs, none the model's."""
    
    # 1. Parse JSON: gestiamo il caso in cui il modello scriva un JSON non valido
    try:
        kwargs = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return "Error: arguments are not valid JSON", True

    # 2. Esistenza del Tool: il modello potrebbe inventarsi un nome
    if name not in DISPATCH:
        return f"Error: tool '{name}' does not exist", True

    # 3. Try/Catch: eseguiamo in modo sicuro. Mai far esplodere il programma
    try:
        result = DISPATCH[name](**kwargs)
        errored = False
    except Exception as e:
        # Passiamo al modello solo il messaggio d'errore, senza lo stack trace o i percorsi dei file
        result = f"Error executing tool: {type(e).__name__} - {str(e)}"
        errored = True

    # 4. Cap the size: trasformiamo in stringa e tagliamo se supera il limite
    if not isinstance(result, str):
        try:
            res_str = json.dumps(result, ensure_ascii=False)
        except TypeError:
            res_str = str(result)
    else:
        res_str = result

    if len(res_str) > MAX_RESULT_CHARS:
        res_str = res_str[:MAX_RESULT_CHARS] + "... [TRUNCATED]"

    return res_str, errored


# --------------------------------------------------------------------------
# TODO 2, 3, 4. The loop and its caps.
# --------------------------------------------------------------------------

def run_task(client, task, model: str = LARGE.name,
             max_steps: int = 6, stall_limit: int = 2,
             system: str = SYSTEM, week: int = 4) -> Run:
    """TODO 2, 3, 4. The whole agent: a while loop with three exits."""
    
    run = Run(task_id=task.id)
    
    # Inizializziamo lo storico dei messaggi
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task.question}
    ]

    seen_doc_ids = set()
    stalls = 0

    # Inizializziamo il registratore (TraceRecorder)
    # Assumiamo che task abbia un attributo 'lang', sennò fallback a 'en'
    lang = getattr(task, 'lang', 'en')
    rec = TraceRecorder(
        week=week, case_id=task.id,
        conditions=local_conditions(model, system="agent", language=lang),
        user_input=task.question
    )

    t0 = time.perf_counter()

    # TODO 3: Il limite di passaggi (step cap). Usiamo un ciclo for anziché while True
    for step in range(max_steps):
        run.steps += 1

        # Chiamata al Modello
        with rec.step("model", model) as model_step:
            reply = client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=messages,
                tools=SCHEMAS
            )
            msg = reply.choices[0].message
            
            # Aggiorniamo i token
            run.tokens += reply.usage.prompt_tokens + reply.usage.completion_tokens
            model_step.tokens(reply.usage.prompt_tokens, reply.usage.completion_tokens)

        # EXIT 1 (Normale): L'IA ha finito, non vuole chiamare strumenti
        if not msg.tool_calls:
            run.answer = msg.content or ""
            break

        # REGOLA FONDAMENTALE (TODO 2): Il messaggio dell'assistente va aggiunto PRIMA dei tool results
        # Convertiamo l'oggetto msg in un dizionario sicuro per il ReplayClient
        assistant_msg = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tcall.id,
                    "type": "function",
                    "function": {
                        "name": tcall.function.name,
                        "arguments": tcall.function.arguments
                    }
                } for tcall in msg.tool_calls
            ]
        
        # Aggiungiamo il dizionario invece dell'oggetto grezzo
        messages.append(assistant_msg)

        searched_in_step = False
        new_docs_in_step = 0

        # Processiamo tutti i tool richiesti in questo giro
        for tcall in msg.tool_calls:
            run.tool_calls.append(tcall.function.name)

            with rec.step("tool", tcall.function.name) as tool_step:
                res_str, errored = run_tool_call(tcall.function.name, tcall.function.arguments)

                if errored:
                    run.tool_errors += 1
                if INJECTION_MARKER in res_str:
                    run.saw_injection = True

                # REGOLA FONDAMENTALE (TODO 2): Aggiungere il risultato con il match al tool_call_id
                messages.append({
                    "role": "tool",
                    "tool_call_id": tcall.id,
                    "name": tcall.function.name,
                    "content": res_str
                })
                
                tool_step.detail(arguments=tcall.function.arguments, result=res_str)

                # TODO 4 (Preparazione): Se il tool è search_services, analizziamo i doc_id
                if tcall.function.name == "search_services":
                    searched_in_step = True
                    docs_found = _doc_ids(res_str)
                    new_docs = docs_found - seen_doc_ids
                    new_docs_in_step += len(new_docs)
                    seen_doc_ids.update(docs_found)

        # TODO 4: Rilevatore di stallo (No-progress detector)
        # Se abbiamo fatto una ricerca, ma non abbiamo trovato nessun documento nuovo, è uno stallo
        if searched_in_step:
            if new_docs_in_step == 0:
                stalls += 1
            else:
                stalls = 0

        # EXIT 2: Raggiunto limite di stallo
        if stalls >= stall_limit:
            run.cap_fired = "stall_limit"
            run.answer = _partial(run, "I made no progress searching (stall limit reached)")
            break

    else:
        # EXIT 3: Abbiamo esaurito i max_steps senza rompere il ciclo
        run.cap_fired = "max_steps"
        run.answer = _partial(run, "I reached the step limit")

    run.seconds = time.perf_counter() - t0
    
    # Finiamo la registrazione indicando "ok" se non è scattato alcun cap
    # Finiamo la registrazione indicando "ok" se non è scattato alcun cap
    rec.finish(output=run.answer, outcome="ok" if run.stopped_cleanly else "error")

    return run


def _partial(run: Run, reason: str) -> str:
    """What a capped run returns. Never an empty string, never a crash.

    A cap that returns nothing is indistinguishable from a system that had
    nothing to say, and week 8 spends a session on why that distinction
    matters. Say what happened and what was known so far.
    """
    return (f"I could not complete this. {reason}, after "
            f"{len(run.tool_calls)} tool call(s). Please telephone the help "
            f"desk on 4796-2222.")


def _doc_ids(tool_result: Any) -> set[str]:
    try:
        parsed = json.loads(tool_result) if isinstance(tool_result, str) \
            else tool_result
    except (json.JSONDecodeError, TypeError):
        return set()
    if not isinstance(parsed, list):
        return set()
    return {h.get("doc_id") for h in parsed
            if isinstance(h, dict) and h.get("doc_id")}
