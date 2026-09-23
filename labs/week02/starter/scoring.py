"""The scorer. Two TODO markers, and it is the most important file today.

A prompt change is not an improvement until it has been measured, and this
is what measures it. Write it before you tune anything, because a scorer
written after you have seen the output tends to score what the output
already does.

One rule, and it decides most of the marks in this session: report per
field, as counts. Never one overall accuracy. Ten records means one error
moves a percentage by ten points, and an average across four fields hides
the only interesting thing in the data, which is that they do not move
together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

FIELDS = ("category", "urgency", "due_date", "quote")


@dataclass
class FieldResult:
    correct: bool
    got: object
    expected: object
    note: str = ""


@dataclass
class Scoreboard:
    """Counts per field, plus the failures worth reading."""

    hits: dict[str, int] = field(
        default_factory=lambda: {f: 0 for f in FIELDS})
    total: int = 0
    invalid: int = 0
    failures: list[tuple[str, str, str]] = field(default_factory=list)

    def as_counts(self) -> str:
        return "  ".join(f"{f} {self.hits[f]:>2}/{self.total}"
                         for f in FIELDS)


# --------------------------------------------------------------------------
# TODO 3. Score one record against its gold annotation.
# --------------------------------------------------------------------------


def score_one(record, gold, document_text: str) -> dict[str, FieldResult]:
    """Compare one extracted record with its gold annotation, per field."""
    results = {}

    # Estrazione robusta: gestisce sia oggetti GoldCase con .expected che dizionari o oggetti diretti
    if isinstance(gold, dict):
        expected_data = gold.get("expected", gold)
    else:
        expected_data = getattr(gold, "expected", gold)

    if isinstance(expected_data, dict):
        g_cat = expected_data.get("category")
        g_urg = expected_data.get("urgency")
        g_due = expected_data.get("due_date")
        g_quo = expected_data.get("quote")
    else:
        g_cat = getattr(expected_data, "category", None)
        g_urg = getattr(expected_data, "urgency", None)
        g_due = getattr(expected_data, "due_date", None)
        g_quo = getattr(expected_data, "quote", None)

    # 1. Category
    results["category"] = FieldResult(
        correct=(record.category == g_cat),
        got=record.category,
        expected=g_cat
    )

    # 2. Urgency
    results["urgency"] = FieldResult(
        correct=(record.urgency == g_urg),
        got=record.urgency,
        expected=g_urg
    )

    # 3. Due Date
    got_date = record.due_date
    if got_date in ("", "null"):
        got_date = None

    results["due_date"] = FieldResult(
        correct=(got_date == g_due),
        got=got_date,
        expected=g_due
    )

    # 4. Quote: corretto se il modello ha estratto una citazione non vuota 
    # che è realmente presente parola per parola nel testo del documento.
    got_quote = record.quote
    is_correct = bool(got_quote) and (got_quote in document_text)

    results["quote"] = FieldResult(
        correct=is_correct,
        got=got_quote,
        expected="Verbatim substring from document"
    )

    return results

# --------------------------------------------------------------------------
# TODO 4. Aggregate.
# --------------------------------------------------------------------------

#def score_all(records, golds, docs) -> Scoreboard:
    """Roll the per record results into per field counts.

    `records` is a list of (ServiceRequest or None). A None means validation
    failed, and it must be counted: increment `invalid`, and count every
    field as wrong for that document. A scorer that silently skips the
    records it could not parse reports a number that improves every time the
    model gets worse, which is the most dangerous kind of metric.

    Append the interesting failures to `failures` as
    (doc_id, field, one line of what went wrong), because at the checkpoint
    you will be asked which records failed and why, not what your average
    was.
    """
    #raise NotImplementedError("TODO 4: aggregate into a Scoreboard")

def score_all(records, golds, docs) -> Scoreboard:
    """Roll the per record results into per field counts."""
    board = Scoreboard()
    board.total = len(records)

    for i, (record, doc) in enumerate(zip(records, docs)):
        # Supporta sia l'accesso a dizionario che ad attributo di classe per i documenti
        doc_id = doc["id"] if isinstance(doc, dict) else doc.id
        doc_text = doc["text"] if isinstance(doc, dict) else doc.text

        # Recuperiamo l'oggetto gold corretto gestendo sia il dizionario che un'eventuale lista
        if isinstance(golds, dict):
            gold = golds.get(doc_id)
        else:
            gold = golds[i]

        # Gestione dei fallimenti totali di validazione (quando il record è None)
        if record is None:
            board.invalid += 1
            board.failures.append((str(doc_id), "ALL", "Record validation failed (restituito None)"))
            continue

        # Valutazione tramite il TODO 3 per i record validi
        field_results = score_one(record, gold, doc_text)

        # Aggiornamento contatori e tracciamento degli errori specifici
        for field_name, result in field_results.items():
            if result.correct:
                board.hits[field_name] += 1
            else:
                error_msg = f"Expected {result.expected!r}, ma il modello ha restituito {result.got!r}"
                board.failures.append((str(doc_id), field_name, error_msg))

    return board


# --------------------------------------------------------------------------
# Given.
# --------------------------------------------------------------------------

def compare(a: Scoreboard, b: Scoreboard, label_a: str, label_b: str) -> str:
    """Two scoreboards side by side, per field, with the movement."""
    lines = [f"{'field':<10} {label_a:>12} {label_b:>12} {'move':>7}"]
    lines.append("-" * 44)
    for f in FIELDS:
        move = b.hits[f] - a.hits[f]
        lines.append(f"{f:<10} {a.hits[f]:>9}/{a.total} {b.hits[f]:>9}/{b.total} "
                     f"{move:>+7d}")
    lines.append(f"{'invalid':<10} {a.invalid:>12} {b.invalid:>12}")
    return "\n".join(lines)
