"""Terminal rendering kept deliberately dependency free."""

from collections.abc import Iterable

from .models import Diagnosis


def render_text(diagnoses: Iterable[Diagnosis]) -> str:
    items = list(diagnoses)
    if not items:
        return "No supported pod failures found."

    blocks: list[str] = []
    for item in items:
        evidence = "\n".join(f"  - {entry.source}: {entry.detail}" for entry in item.evidence)
        blocks.append(
            f"[{item.severity.upper()}] {item.resource}: {item.title}\n"
            f"  {item.summary}\n"
            f"  Evidence:\n{evidence or '  - none'}\n"
            f"  Fix: {item.fix_command}"
        )
    return "\n\n".join(blocks)

