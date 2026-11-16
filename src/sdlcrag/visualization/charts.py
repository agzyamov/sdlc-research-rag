"""Chart series for the web dashboards (rendered as bar lists in `web/`)."""

from sdlcrag.core.models import FacetCount, SdlcPhase


def phase_label(phase: SdlcPhase) -> str:
    return f"{phase.number}. {phase.display_name}"


def phase_series(slices: list[FacetCount]) -> list[dict]:
    """Papers per SDLC phase, all phases in lifecycle order (zeros kept: honest absence):
    [{"phase", "label", "count"}]."""
    counts = {s.label: s.count for s in slices}
    return [
        {"phase": p.value, "label": phase_label(p), "count": counts.get(p.value, 0)}
        for p in SdlcPhase
    ]


def top_series(slices: list[FacetCount]) -> list[dict]:
    """Most frequent values of one fact type, largest first: [{"label", "count"}]."""
    ordered = sorted(slices, key=lambda s: (-s.count, s.label))
    return [{"label": s.label, "count": s.count} for s in ordered]
