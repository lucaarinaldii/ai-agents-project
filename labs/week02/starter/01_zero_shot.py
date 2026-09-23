"""Block 2. The zero-shot baseline, scored per field.

    python 01_zero_shot.py --replay     # the shipped recording, instant
    python 01_zero_shot.py              # your own model, about 45 seconds

Develop your scorer against `--replay`. The recording holds every model
answer for both variants, so your scorer runs in well under a second and you
can iterate on it properly instead of waiting forty-five seconds to find out
you compared the wrong field.

The recording contains real failures, because the model really does make
them. If your scorer reports forty out of forty, your scorer does nothing.

One TODO marker here. TODO 1 to 4 live in extractor.py and scoring.py, and
this file will not run until they are done.
"""

from __future__ import annotations

import argparse

from documents import DOCS, GOLD
from extractor import (PROMPT_VERSION, SYSTEM_ZERO_SHOT, get_client,
                       run_variant)

from project.trace import write_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = get_client(args.replay)
    board, records, metas = run_variant(client, SYSTEM_ZERO_SHOT,
                                        "zero-shot", DOCS, GOLD)

    if board.failures:
        print("failures worth reading:")
        for doc_id, fieldname, note in board.failures[:10]:
            print(f"  {doc_id}  {fieldname:<9} {note}")

    write_json("artifacts/week02_zero_shot.json", {
        "variant": "zero-shot",
        "prompt_version": PROMPT_VERSION,
        "hits": board.hits, "total": board.total, "invalid": board.invalid,
    })

   # TODO 7. Write the gold set into the project spine.
    cases = []
    for doc, gold in zip(DOCS, GOLD):
        # Ricaviamo i dati in modo sicuro sia che doc/gold siano oggetti o dizionari
        doc_id = getattr(doc, "id", None) or doc.get("id")
        doc_text = getattr(doc, "text", None) or doc.get("text")
        doc_lang = getattr(doc, "lang", "en") if not isinstance(doc, dict) else doc.get("lang", "en")
        
        # Gestione di gold come dict o oggetto
        g_cat = gold.get("category") if isinstance(gold, dict) else getattr(gold, "category", "")
        g_urg = gold.get("urgency") if isinstance(gold, dict) else getattr(gold, "urgency", "")
        g_due = gold.get("due_date") if isinstance(gold, dict) else getattr(gold, "due_date", None)
        
        behavior_date = f"with due date {g_due}" if g_due else "with no due date because none is explicitly stated"
        behavior = f"extracts category {g_cat} and urgency {g_urg}, {behavior_date}."
        
        case_dict = {
            "case_id": doc_id,
            "week_added": 2,
            "question": doc_text,
            "expected": gold if isinstance(gold, dict) else {"category": g_cat, "urgency": g_urg, "due_date": g_due, "quote": getattr(gold, "quote", "")},
            "expected_behavior": behavior,
            "slice_tags": [f"lang:{doc_lang}"]
        }
        cases.append(case_dict)
        
    write_json("artifacts/goldset.json", {"cases": cases})


if __name__ == "__main__":
    raise SystemExit(main())
