"""Small helpers for claim type strings and numeric proximity (stdlib-only; safe for tests)."""


def claim_type_label_lower(claim_type_result):
    """Normalize claim type from classifier output to a lowercase string (handles Enum)."""
    if not isinstance(claim_type_result, dict):
        return str(claim_type_result or "").lower()
    t = claim_type_result.get("type")
    if t is None:
        return ""
    if isinstance(t, str):
        return t.lower()
    val = getattr(t, "value", None)
    if isinstance(val, str):
        return val.lower()
    return str(val if val is not None else t).lower()


def collect_non_year_numeric_values(num_strings):
    """Parse numeric tokens; drop years and near-zero values."""

    def is_year_token(n):
        try:
            return 1000 <= int(n) <= 2100
        except (ValueError, TypeError):
            return False

    def parse_num(s):
        try:
            return float(s.replace(",", ""))
        except (ValueError, TypeError):
            return None

    out = []
    for n in num_strings:
        v = parse_num(n)
        if v is None or abs(v) < 1e-12:
            continue
        if is_year_token(n):
            continue
        out.append(v)
    return out


def best_numeric_pairwise_rel_diff(claim_vals, ev_vals):
    """Minimum relative difference between any claim value and any evidence value."""
    if not claim_vals or not ev_vals:
        return None
    best = float("inf")
    for cv in claim_vals:
        for evv in ev_vals:
            denom = max(abs(cv), abs(evv), 1e-12)
            rd = abs(cv - evv) / denom
            if rd < best:
                best = rd
    return best
