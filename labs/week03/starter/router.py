"""The classifier and the policy layer. TODO 2 and 3.

Two calls per request in the routed system: one to decide, one to answer.
The first is cheap and its output is inspectable. The second is the work.

The policy layer between them is about three lines of code and three design
decisions, and the decisions are where the marks are.
"""

from __future__ import annotations

#from project.models import BASE_URL, API_KEY, SMALL

import time
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from routes import ROUTES, SPECIALISTS, SYSTEM_ROUTER

from project.models import BASE_URL, API_KEY, SMALL


class Decision(BaseModel):
    route: Literal["request", "info", "status", "complaint", "other"]
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(max_length=200)


class Routed(BaseModel):
    """What the policy layer decided, and why."""

    decision: Decision
    applied_route: str
    policy_fired: str | None = None      # None means the decision stood
    evidence_ok: bool = True


# --------------------------------------------------------------------------
# TODO 2. The classifying call.
# --------------------------------------------------------------------------

import time
from pydantic import ValidationError
import json

def classify(client, text: str, model: str = SMALL.name,
             temperature: float = 0.0) -> tuple[Decision | None, dict]:
    """One cheap call whose only job is to pick a route."""
    
    t0 = time.perf_counter()
    
    # 1. Definiamo lo schema Pydantic come strumento (tool) che il modello deve chiamare
    tools = [
        {
            "type": "function",
            "function": {
                "name": "submit_decision",
                "description": "Submit the classification decision for the ticket.",
                "parameters": Decision.model_json_schema()
            }
        }
    ]

    try:
        # 2. Chiamata API identica alla week 2
        reply = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": SYSTEM_ROUTER},
                {"role": "user", "content": text}
            ],
            # Costringiamo il modello a usare la nostra funzione (schema)
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "submit_decision"}}
        )
        
        # 3. Estraiamo gli argomenti della funzione generata dal modello
        tool_calls = reply.choices[0].message.tool_calls
        
        if not tool_calls:
            # Fallimento del modello nel chiamare la funzione
            raise ValueError("No tool call generated")
            
        raw_args = tool_calls[0].function.arguments
        
        # 4. Validazione Pydantic degli argomenti (fallirà qui se il JSON è malformato)
        decision = Decision.model_validate_json(raw_args)
        
        meta = {
            "seconds": time.perf_counter() - t0,
            "prompt_tokens": reply.usage.prompt_tokens,
            "completion_tokens": reply.usage.completion_tokens,
            "raw": raw_args
        }
        
        return decision, meta

    # 5. Gestione del fallimento (ValidationError o problemi di parsing)
    except (ValidationError, json.JSONDecodeError, ValueError) as e:
        # Se c'è un errore, restituiamo None e salviamo i dati grezzi che abbiamo
        
        prompt_tokens = 0
        completion_tokens = 0
        raw_output = str(e)
        
        # Cerchiamo di recuperare i token usage se la chiamata è andata a buon fine ma il parsing è fallito
        if 'reply' in locals() and hasattr(reply, 'usage') and reply.usage is not None:
            prompt_tokens = reply.usage.prompt_tokens
            completion_tokens = reply.usage.completion_tokens
            if hasattr(reply.choices[0].message, 'content') and reply.choices[0].message.content:
                 raw_output = reply.choices[0].message.content
            elif hasattr(reply.choices[0].message, 'tool_calls') and reply.choices[0].message.tool_calls:
                 raw_output = reply.choices[0].message.tool_calls[0].function.arguments

        meta = {
            "seconds": time.perf_counter() - t0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "raw": raw_output
        }
        return None, meta


# --------------------------------------------------------------------------
# TODO 3. The policy layer.
# --------------------------------------------------------------------------

# TODO 3a. Pick a number, but look at the distribution before you pick it.
#
# Choosing a threshold because 0.7 sounds reasonable is the mistake this
# exercise exists to catch. Run the classifier over the twenty four queries
# first, print the confidences, and then decide. On one of the two course
# models the answer will surprise you.
CONFIDENCE_FLOOR = 0.98

# TODO 3b. Where does anything the policy rejects go?
#
# Not every route is equally safe to be wrong into. Ask what each specialist
# DOES on the sender's behalf, and pick the one whose actions are easiest to
# undo. One of the five logs a ticket, one escalates to a human, and one
# only answers. That should decide it.
SAFE_DEFAULT = "info"


def apply_policy(decision: Decision | None, text: str) -> Routed:
    """Take a Decision and return what will actually happen."""

    # 1. Nessuna decisione valida (il modello ha fallito il JSON o ha crashato)
    if decision is None:
        # Dato che la classe Routed richiede obbligatoriamente un oggetto Decision,
        # ne creiamo uno fittizio di fallback.
        fallback_decision = Decision(
            route=SAFE_DEFAULT, 
            confidence=0.0, 
            evidence="Validation Failed"
        )
        return Routed(
            decision=fallback_decision,
            applied_route=SAFE_DEFAULT,
            policy_fired="validation_failed",
            evidence_ok=False
        )

    # Controlliamo l'evidence per usarla nei prossimi step
    # Rimuoviamo gli spazi vuoti agli estremi per evitare falsi negativi dovuti alla formattazione
    is_evidence_real = decision.evidence.strip() in text

    # 2. Controllo dell'Evidence: la citazione è un'allucinazione?
    if not is_evidence_real:
        return Routed(
            decision=decision,
            applied_route=SAFE_DEFAULT,
            policy_fired="fabricated_evidence",
            evidence_ok=False
        )

    # 3. Controllo della Confidence: il modello era troppo insicuro?
    if decision.confidence < CONFIDENCE_FLOOR:
        return Routed(
            decision=decision,
            applied_route=SAFE_DEFAULT,
            policy_fired="low_confidence",
            evidence_ok=is_evidence_real
        )

    # Se supera tutti e tre i controlli, la decisione del modello viene approvata!
    return Routed(
        decision=decision,
        applied_route=decision.route, # Usiamo la rotta scelta dal modello
        policy_fired=None,            # Nessuna policy è scattata (tutto ok)
        evidence_ok=True
    )


# --------------------------------------------------------------------------
# Given. The answering call.
# --------------------------------------------------------------------------

def respond(client, system: str, text: str,
            model: str = SMALL.name) -> tuple[str, dict]:
    t0 = time.perf_counter()
    reply = client.chat.completions.create(
        model=model, temperature=0.0, max_tokens=250,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": text}])
    return reply.choices[0].message.content, {
        "seconds": time.perf_counter() - t0,
        "prompt_tokens": reply.usage.prompt_tokens,
        "completion_tokens": reply.usage.completion_tokens,
    }

'''
if __name__ == "__main__":
    from queries import QUERIES
    from openai import OpenAI
    
    # Importiamo le costanti dal modulo del tuo progetto.
    # (Assicurati che queste costanti siano importate correttamente all'inizio del file)
    from project.models import API_KEY, BASE_URL
    
    # Inizializziamo il client direttamente
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    print(f"{'ID':<6} | {'GOLD ROUTE':<10} | {'PREDICTED':<10} | {'CONFIDENCE':<10} | {'EVIDENCE OK?':<12}")
    print("-" * 60)
    
    for q in QUERIES:
        decision, meta = classify(client, q.text)
        
        if decision is None:
             print(f"{q.id:<6} | {q.route:<10} | {'FAILED':<10} | {'N/A':<10} | {'N/A':<12}")
             continue
             
        evidence_ok = decision.evidence.strip() in q.text
        
        predicted_route = decision.route
        if predicted_route != q.route:
            predicted_route = f"*{predicted_route}*"
            
        print(f"{q.id:<6} | {q.route:<10} | {predicted_route:<10} | {decision.confidence:<10.2f} | {str(evidence_ok):<12}")

    print("-" * 60)
    print("\nIstruzioni:")
    print("1. Guarda i valori nella colonna CONFIDENCE.")
    print("2. Cerca le righe dove la predizione differisce dalla GOLD ROUTE (marcate con *).")
    print("3. Scegli CONFIDENCE_FLOOR per scartare gli errori senza bloccare i successi.")

'''