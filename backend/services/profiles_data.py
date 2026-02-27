"""Standard metal profiles database for metalworkers (Fabbri)."""

STANDARD_PROFILES = [
    # --- TUBOLARI QUADRI ---
    {"profile_id": "TQ-20x20x2", "type": "tubolare", "label": "Tubolare 20x20x2", "dimensions": "20x20x2 mm", "weight_per_meter": 1.12, "surface_per_meter": 0.080},
    {"profile_id": "TQ-25x25x2", "type": "tubolare", "label": "Tubolare 25x25x2", "dimensions": "25x25x2 mm", "weight_per_meter": 1.42, "surface_per_meter": 0.100},
    {"profile_id": "TQ-30x30x2", "type": "tubolare", "label": "Tubolare 30x30x2", "dimensions": "30x30x2 mm", "weight_per_meter": 1.72, "surface_per_meter": 0.120},
    {"profile_id": "TQ-30x30x3", "type": "tubolare", "label": "Tubolare 30x30x3", "dimensions": "30x30x3 mm", "weight_per_meter": 2.49, "surface_per_meter": 0.120},
    {"profile_id": "TQ-40x40x2", "type": "tubolare", "label": "Tubolare 40x40x2", "dimensions": "40x40x2 mm", "weight_per_meter": 2.32, "surface_per_meter": 0.160},
    {"profile_id": "TQ-40x40x3", "type": "tubolare", "label": "Tubolare 40x40x3", "dimensions": "40x40x3 mm", "weight_per_meter": 3.39, "surface_per_meter": 0.160},
    {"profile_id": "TQ-50x50x2", "type": "tubolare", "label": "Tubolare 50x50x2", "dimensions": "50x50x2 mm", "weight_per_meter": 2.93, "surface_per_meter": 0.200},
    {"profile_id": "TQ-50x50x3", "type": "tubolare", "label": "Tubolare 50x50x3", "dimensions": "50x50x3 mm", "weight_per_meter": 4.29, "surface_per_meter": 0.200},
    {"profile_id": "TQ-60x60x3", "type": "tubolare", "label": "Tubolare 60x60x3", "dimensions": "60x60x3 mm", "weight_per_meter": 5.19, "surface_per_meter": 0.240},
    {"profile_id": "TQ-80x80x3", "type": "tubolare", "label": "Tubolare 80x80x3", "dimensions": "80x80x3 mm", "weight_per_meter": 6.99, "surface_per_meter": 0.320},
    {"profile_id": "TQ-100x100x3", "type": "tubolare", "label": "Tubolare 100x100x3", "dimensions": "100x100x3 mm", "weight_per_meter": 8.79, "surface_per_meter": 0.400},
    # --- TUBOLARI RETTANGOLARI ---
    {"profile_id": "TR-60x40x2", "type": "tubolare", "label": "Tubolare 60x40x2", "dimensions": "60x40x2 mm", "weight_per_meter": 2.93, "surface_per_meter": 0.200},
    {"profile_id": "TR-60x40x3", "type": "tubolare", "label": "Tubolare 60x40x3", "dimensions": "60x40x3 mm", "weight_per_meter": 4.29, "surface_per_meter": 0.200},
    {"profile_id": "TR-80x40x3", "type": "tubolare", "label": "Tubolare 80x40x3", "dimensions": "80x40x3 mm", "weight_per_meter": 5.19, "surface_per_meter": 0.240},
    {"profile_id": "TR-100x50x3", "type": "tubolare", "label": "Tubolare 100x50x3", "dimensions": "100x50x3 mm", "weight_per_meter": 6.59, "surface_per_meter": 0.300},
    {"profile_id": "TR-120x60x3", "type": "tubolare", "label": "Tubolare 120x60x3", "dimensions": "120x60x3 mm", "weight_per_meter": 7.99, "surface_per_meter": 0.360},
    # --- PIATTI ---
    {"profile_id": "PT-20x3", "type": "piatto", "label": "Piatto 20x3", "dimensions": "20x3 mm", "weight_per_meter": 0.47, "surface_per_meter": 0.040},
    {"profile_id": "PT-25x3", "type": "piatto", "label": "Piatto 25x3", "dimensions": "25x3 mm", "weight_per_meter": 0.59, "surface_per_meter": 0.050},
    {"profile_id": "PT-30x3", "type": "piatto", "label": "Piatto 30x3", "dimensions": "30x3 mm", "weight_per_meter": 0.71, "surface_per_meter": 0.060},
    {"profile_id": "PT-30x5", "type": "piatto", "label": "Piatto 30x5", "dimensions": "30x5 mm", "weight_per_meter": 1.18, "surface_per_meter": 0.060},
    {"profile_id": "PT-40x3", "type": "piatto", "label": "Piatto 40x3", "dimensions": "40x3 mm", "weight_per_meter": 0.94, "surface_per_meter": 0.080},
    {"profile_id": "PT-40x5", "type": "piatto", "label": "Piatto 40x5", "dimensions": "40x5 mm", "weight_per_meter": 1.57, "surface_per_meter": 0.080},
    {"profile_id": "PT-50x5", "type": "piatto", "label": "Piatto 50x5", "dimensions": "50x5 mm", "weight_per_meter": 1.96, "surface_per_meter": 0.100},
    {"profile_id": "PT-50x8", "type": "piatto", "label": "Piatto 50x8", "dimensions": "50x8 mm", "weight_per_meter": 3.14, "surface_per_meter": 0.100},
    {"profile_id": "PT-60x5", "type": "piatto", "label": "Piatto 60x5", "dimensions": "60x5 mm", "weight_per_meter": 2.36, "surface_per_meter": 0.120},
    {"profile_id": "PT-60x8", "type": "piatto", "label": "Piatto 60x8", "dimensions": "60x8 mm", "weight_per_meter": 3.77, "surface_per_meter": 0.120},
    {"profile_id": "PT-80x8", "type": "piatto", "label": "Piatto 80x8", "dimensions": "80x8 mm", "weight_per_meter": 5.02, "surface_per_meter": 0.160},
    {"profile_id": "PT-100x10", "type": "piatto", "label": "Piatto 100x10", "dimensions": "100x10 mm", "weight_per_meter": 7.85, "surface_per_meter": 0.200},
    # --- ANGOLARI ---
    {"profile_id": "AL-20x20x3", "type": "angolare", "label": "Angolare 20x20x3", "dimensions": "20x20x3 mm", "weight_per_meter": 0.88, "surface_per_meter": 0.080},
    {"profile_id": "AL-25x25x3", "type": "angolare", "label": "Angolare 25x25x3", "dimensions": "25x25x3 mm", "weight_per_meter": 1.12, "surface_per_meter": 0.100},
    {"profile_id": "AL-30x30x3", "type": "angolare", "label": "Angolare 30x30x3", "dimensions": "30x30x3 mm", "weight_per_meter": 1.36, "surface_per_meter": 0.120},
    {"profile_id": "AL-40x40x3", "type": "angolare", "label": "Angolare 40x40x3", "dimensions": "40x40x3 mm", "weight_per_meter": 1.84, "surface_per_meter": 0.160},
    {"profile_id": "AL-40x40x4", "type": "angolare", "label": "Angolare 40x40x4", "dimensions": "40x40x4 mm", "weight_per_meter": 2.42, "surface_per_meter": 0.160},
    {"profile_id": "AL-50x50x4", "type": "angolare", "label": "Angolare 50x50x4", "dimensions": "50x50x4 mm", "weight_per_meter": 3.06, "surface_per_meter": 0.200},
    {"profile_id": "AL-50x50x5", "type": "angolare", "label": "Angolare 50x50x5", "dimensions": "50x50x5 mm", "weight_per_meter": 3.77, "surface_per_meter": 0.200},
    {"profile_id": "AL-60x60x5", "type": "angolare", "label": "Angolare 60x60x5", "dimensions": "60x60x5 mm", "weight_per_meter": 4.57, "surface_per_meter": 0.240},
    {"profile_id": "AL-60x60x6", "type": "angolare", "label": "Angolare 60x60x6", "dimensions": "60x60x6 mm", "weight_per_meter": 5.42, "surface_per_meter": 0.240},
    {"profile_id": "AL-80x80x6", "type": "angolare", "label": "Angolare 80x80x6", "dimensions": "80x80x6 mm", "weight_per_meter": 7.34, "surface_per_meter": 0.320},
    # --- TONDI ---
    {"profile_id": "TN-10", "type": "tondo", "label": "Tondo pieno 10", "dimensions": "D10 mm", "weight_per_meter": 0.62, "surface_per_meter": 0.031},
    {"profile_id": "TN-12", "type": "tondo", "label": "Tondo pieno 12", "dimensions": "D12 mm", "weight_per_meter": 0.89, "surface_per_meter": 0.038},
    {"profile_id": "TN-14", "type": "tondo", "label": "Tondo pieno 14", "dimensions": "D14 mm", "weight_per_meter": 1.21, "surface_per_meter": 0.044},
    {"profile_id": "TN-16", "type": "tondo", "label": "Tondo pieno 16", "dimensions": "D16 mm", "weight_per_meter": 1.58, "surface_per_meter": 0.050},
    {"profile_id": "TN-20", "type": "tondo", "label": "Tondo pieno 20", "dimensions": "D20 mm", "weight_per_meter": 2.47, "surface_per_meter": 0.063},
]

PROFILE_TYPES = [
    {"value": "tubolare", "label": "Tubolari"},
    {"value": "piatto", "label": "Piatti"},
    {"value": "angolare", "label": "Angolari"},
    {"value": "tondo", "label": "Tondi"},
]

BAR_LENGTH_MM = 6000  # Standard bar length: 6 meters


def get_profiles_by_type(profile_type: str = None):
    """Get profiles filtered by type."""
    if profile_type:
        return [p for p in STANDARD_PROFILES if p["type"] == profile_type]
    return STANDARD_PROFILES


def get_profile_by_id(profile_id: str):
    """Get a single profile by ID."""
    for p in STANDARD_PROFILES:
        if p["profile_id"] == profile_id:
            return p
    return None


def calculate_bars_needed(items: list, bar_length_mm: int = BAR_LENGTH_MM) -> list:
    """
    Calculate how many standard bars are needed.
    Groups by profile_id, then divides total length by bar length.
    """
    profile_groups = {}

    for item in items:
        pid = item.get("profile_id") or item.get("name", "unknown")
        length_mm = float(item.get("length_mm", 0))
        qty = float(item.get("quantity", 1))

        if pid not in profile_groups:
            profile_groups[pid] = {
                "profile_id": pid,
                "profile_label": item.get("profile_label", pid),
                "cuts": [],
                "total_length_mm": 0,
            }

        for _ in range(int(qty)):
            profile_groups[pid]["cuts"].append(length_mm)
            profile_groups[pid]["total_length_mm"] += length_mm

    results = []
    for pid, group in profile_groups.items():
        total_mm = group["total_length_mm"]
        bars_needed = -(-int(total_mm) // bar_length_mm)  # ceil division
        waste_mm = (bars_needed * bar_length_mm) - total_mm
        waste_pct = (waste_mm / (bars_needed * bar_length_mm) * 100) if bars_needed > 0 else 0

        results.append({
            "profile_id": pid,
            "profile_label": group["profile_label"],
            "cuts": sorted(group["cuts"], reverse=True),
            "total_length_mm": round(total_mm, 1),
            "total_length_m": round(total_mm / 1000, 3),
            "bar_length_mm": bar_length_mm,
            "bars_needed": max(bars_needed, 0),
            "waste_mm": round(waste_mm, 1),
            "waste_percent": round(waste_pct, 1),
        })

    return sorted(results, key=lambda x: x["profile_label"])
