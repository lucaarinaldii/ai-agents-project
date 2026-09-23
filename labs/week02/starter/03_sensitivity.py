"""Block 4. Change one thing nobody would flag in review, and measure it.

    python 03_sensitivity.py --variant role --replay
    python 03_sensitivity.py --variant english_only

Fifteen minutes, one variant per group, so that the plenary has four results
instead of one. Your instructor will assign you one.

The point of this block is not which variant wins. It is that a change no
reviewer would comment on moves a measured number, which is why a prompt is
a versioned artifact and why "I improved the prompt" is not a claim anybody
should accept without a table.

One TODO marker.
"""

from __future__ import annotations

import argparse

from documents import DOCS, GOLD
from extractor import SYSTEM_ZERO_SHOT, get_client, run_variant
from scoring import compare

from project.trace import write_json

VARIANTS = ("baseline", "role", "reordered", "no_delimiter", "english_only")


# --------------------------------------------------------------------------
# TODO 8. Build one variant and measure it against your few-shot baseline.
# --------------------------------------------------------------------------

def build_system(variant: str) -> str:
    """Return the system prompt for one variant."""
    
    # 1. Componenti base del nostro prompt few-shot
    intro = "Here are some examples of correct extractions:\n"
    
    # Esempi originali multilingua (Inglese, Francese, Tedesco)
    ex1_en = 'Example 1:\nMessage: "The badge reader at the side entrance rejects my card since the system update. I can still get in through the main door, so it is not blocking me."\nOutput:\n{"category": "access", "urgency": "standard", "due_date": null, "quote": "it is not blocking me."}\n'
    
    ex2_fr = 'Example 2:\nMessage: "L\'ascenseur du batiment administratif est bloque entre le rez et le premier avec une personne a l\'interieur. Intervention immediate necessaire."\nOutput:\n{"category": "facilities", "urgency": "urgent", "due_date": null, "quote": "Intervention immediate necessaire."}\n'
    
    ex3_de = 'Example 3:\nMessage: "Der Laptop aus dem Sitzungssaal laedt nicht mehr, das Netzteil ist vermutlich defekt. Ersatz waere bis zum 20/09/2026 gut."\nOutput:\n{"category": "hardware", "urgency": "standard", "due_date": "2026-09-20", "quote": "Ersatz waere bis zum 20/09/2026 gut."}\n'

    # 2. Esempi alternativi solo in inglese (da EXAMPLE_POOL EX-04 ed EX-06) per la variante "english_only"
    ex4_en = 'Example 2:\nMessage: "For information only: the new intranet search will be switched on next week. Nothing changes for users."\nOutput:\n{"category": "other", "urgency": "info", "due_date": null, "quote": "For information only:"}\n'
    
    ex6_en = 'Example 3:\nMessage: "The window in office 2.14 will not close and rain is coming in onto the shared printer below it. This is getting worse by the hour."\nOutput:\n{"category": "facilities", "urgency": "urgent", "due_date": null, "quote": "This is getting worse by the hour."}\n'

    # Costruzione delle varianti
    if variant == "baseline":
        return SYSTEM_ZERO_SHOT + "\n" + intro + "\n" + ex1_en + "\n" + ex2_fr + "\n" + ex3_de

    elif variant == "role":
        # Aggiunge un ruolo fittizio all'inizio
        return "You are a senior service desk analyst.\n" + SYSTEM_ZERO_SHOT + "\n" + intro + "\n" + ex1_en + "\n" + ex2_fr + "\n" + ex3_de

    elif variant == "reordered":
        # Inverte l'ordine: Tedesco, Francese, Inglese
        return SYSTEM_ZERO_SHOT + "\n" + intro + "\n" + ex3_de + "\n" + ex2_fr + "\n" + ex1_en

    elif variant == "no_delimiter":
        # Rimuove i separatori testuali standard (es. "---") dal prompt di sistema
        base = SYSTEM_ZERO_SHOT + "\n" + intro + "\n" + ex1_en + "\n" + ex2_fr + "\n" + ex3_de
        return base.replace("---", "").replace("###", "")

    elif variant == "english_only":
        # Sostituisce i ticket FR e DE con quelli EN
        return SYSTEM_ZERO_SHOT + "\n" + intro + "\n" + ex1_en + "\n" + ex4_en + "\n" + ex6_en

    else:
        raise ValueError(f"Unknown variant: {variant}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=VARIANTS, required=True)
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = get_client(args.replay)

    base = run_variant(client, build_system("baseline"), "baseline",
                       DOCS, GOLD)[0]
    if args.variant == "baseline":
        return 0
    other = run_variant(client, build_system(args.variant), args.variant,
                        DOCS, GOLD)[0]

    print(compare(base, other, "baseline", args.variant))

    # Per language, which is where the english_only variant shows its hand
    # and where an overall average would have hidden it entirely.
    for lang in ("en", "fr", "de"):
        ids = {d.id for d in DOCS if d.lang == lang}
        n = len(ids)
        print(f"  {lang}: {n} documents"
              f"   baseline field errors "
              f"{sum(1 for f in base.failures if f[0] in ids)}"
              f"   {args.variant} field errors "
              f"{sum(1 for f in other.failures if f[0] in ids)}")

    write_json(f"artifacts/week02_sensitivity_{args.variant}.json", {
        "variant": args.variant,
        "baseline_hits": base.hits, "variant_hits": other.hits,
    })

    # Write in DECISIONS.md: what you changed, what moved, and by how much.
    # If nothing moved, say so. A variant that changes nothing measurable is
    # a real result and it is worth reporting, because it tells the room
    # which knobs are worth arguing about and which are superstition.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
