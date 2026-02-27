"""
Ottimizzatore di Taglio Avanzato — 1D Bin Packing (First Fit Decreasing).

Minimizes material waste by optimally placing cuts onto standard bars.
Supports configurable bar length and blade kerf (saw cut width).
"""
from typing import List, Dict, Any


DEFAULT_BAR_LENGTH_MM = 6000
DEFAULT_KERF_MM = 3  # Saw blade thickness


def optimize_cutting(
    items: List[Dict[str, Any]],
    bar_length_mm: int = DEFAULT_BAR_LENGTH_MM,
    kerf_mm: float = DEFAULT_KERF_MM,
) -> Dict[str, Any]:
    """
    Run the FFD bin-packing optimizer on BOM items.

    Groups items by profile_id, then for each group:
    - Expands quantity into individual cuts
    - Sorts cuts descending (First Fit Decreasing)
    - Places each cut into the first bar with enough room

    Returns a complete cutting plan with bar layouts and statistics.
    """
    # Group by profile
    profile_groups: Dict[str, Dict] = {}
    for item in items:
        pid = item.get("profile_id") or item.get("name", "sconosciuto")
        label = item.get("profile_label") or item.get("name", pid)
        length_mm = float(item.get("length_mm", 0))
        qty = int(float(item.get("quantity", 1)))
        weight_m = float(item.get("weight_per_meter", 0))
        cost_unit = float(item.get("cost_per_unit", 0))

        if length_mm <= 0:
            continue

        if pid not in profile_groups:
            profile_groups[pid] = {
                "profile_id": pid,
                "profile_label": label,
                "weight_per_meter": weight_m,
                "cost_per_unit": cost_unit,
                "cuts": [],
            }

        for _ in range(qty):
            profile_groups[pid]["cuts"].append(length_mm)

    # Optimize each profile group
    profile_results = []
    grand_total_bars = 0
    grand_total_waste = 0.0
    grand_total_used = 0.0

    for pid, group in sorted(profile_groups.items(), key=lambda x: x[1]["profile_label"]):
        bars = _ffd_pack(group["cuts"], bar_length_mm, kerf_mm)
        n_bars = len(bars)
        grand_total_bars += n_bars

        total_waste = 0.0
        total_used = 0.0
        bar_details = []

        for bar_idx, bar in enumerate(bars):
            used = sum(c["length_mm"] for c in bar["cuts"])
            kerf_total = kerf_mm * len(bar["cuts"])
            waste = bar_length_mm - used - kerf_total
            if waste < 0:
                waste = 0
            total_waste += waste
            total_used += used

            bar_details.append({
                "bar_index": bar_idx + 1,
                "cuts": bar["cuts"],
                "used_mm": round(used, 1),
                "kerf_mm": round(kerf_total, 1),
                "waste_mm": round(waste, 1),
                "waste_percent": round((waste / bar_length_mm) * 100, 1) if bar_length_mm > 0 else 0,
                "fill_percent": round(((used + kerf_total) / bar_length_mm) * 100, 1) if bar_length_mm > 0 else 0,
            })

        grand_total_waste += total_waste
        grand_total_used += total_used

        waste_pct = round((total_waste / (n_bars * bar_length_mm)) * 100, 1) if n_bars > 0 else 0
        weight_total = round((total_used / 1000) * group["weight_per_meter"], 2)

        profile_results.append({
            "profile_id": pid,
            "profile_label": group["profile_label"],
            "weight_per_meter": group["weight_per_meter"],
            "total_cuts": len(group["cuts"]),
            "bars_needed": n_bars,
            "bar_length_mm": bar_length_mm,
            "bars": bar_details,
            "total_used_mm": round(total_used, 1),
            "total_waste_mm": round(total_waste, 1),
            "waste_percent": waste_pct,
            "estimated_weight_kg": weight_total,
        })

    grand_waste_pct = round(
        (grand_total_waste / (grand_total_bars * bar_length_mm)) * 100, 1
    ) if grand_total_bars > 0 else 0

    return {
        "bar_length_mm": bar_length_mm,
        "kerf_mm": kerf_mm,
        "profiles": profile_results,
        "summary": {
            "total_bars": grand_total_bars,
            "total_used_mm": round(grand_total_used, 1),
            "total_waste_mm": round(grand_total_waste, 1),
            "waste_percent": grand_waste_pct,
            "total_cuts": sum(len(g["cuts"]) for g in profile_groups.values()),
        },
    }


def _ffd_pack(
    cuts: List[float],
    bar_length_mm: int,
    kerf_mm: float,
) -> List[Dict]:
    """
    First Fit Decreasing bin-packing.

    Each bar tracks remaining capacity. Each cut consumes length + kerf.
    Returns list of bars, each with positioned cuts.
    """
    sorted_cuts = sorted(cuts, reverse=True)
    bars: List[Dict] = []

    for cut_length in sorted_cuts:
        placed = False
        space_needed = cut_length + kerf_mm

        for bar in bars:
            if bar["remaining"] >= space_needed:
                offset = bar_length_mm - bar["remaining"]
                bar["cuts"].append({
                    "length_mm": cut_length,
                    "offset_mm": round(offset, 1),
                })
                bar["remaining"] -= space_needed
                placed = True
                break

        if not placed:
            new_bar = {
                "remaining": bar_length_mm - space_needed,
                "cuts": [{
                    "length_mm": cut_length,
                    "offset_mm": 0,
                }],
            }
            bars.append(new_bar)

    return bars
