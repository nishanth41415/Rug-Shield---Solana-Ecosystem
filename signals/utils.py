"""Shared helpers for signal output and data-quality tagging."""

NEUTRAL_SCORE = 0.5

# Risk labels for non-evidence signals (not counted as LOW/MEDIUM/HIGH/CRITICAL)
RISK_UNAVAILABLE = "UNAVAILABLE"
RISK_FALLBACK = "FALLBACK"


def set_data_source(signal: dict, data_source: str) -> dict:
    """Attach data_source to a signal dict (real | mock | fallback | unavailable)."""
    signal.setdefault("details", {})["data_source"] = data_source
    return signal


def mark_non_evidence(signal: dict, data_source: str) -> dict:
    """
    Tag a signal as unavailable or fallback — not real risk evidence.
    Sets risk_level to UNAVAILABLE/FALLBACK and score to None for display.
    """
    signal = set_data_source(signal, data_source)
    if data_source == "unavailable":
        signal["risk_level"] = RISK_UNAVAILABLE
    elif data_source in ("mock", "fallback"):
        signal["risk_level"] = RISK_FALLBACK
    else:
        return signal
    signal["score"] = None
    signal["details"]["evidence_status"] = signal["risk_level"]
    return signal


def tag_build_result(build_fn, data_source: str, *args, **kwargs) -> dict:
    """Call a module _build() and tag the result with data_source."""
    result = build_fn(*args, **kwargs)
    if data_source in ("unavailable", "mock", "fallback"):
        return mark_non_evidence(result, data_source)
    return set_data_source(result, data_source)
