"""
Sprint 1 — Apply @require_role() decorators to all route files.

Groups routes by functional domain and applies the correct role set.
Safe to re-run: checks if require_role is already imported before patching.
"""
import re
import os

ROUTES_DIR = os.path.join(os.path.dirname(__file__), "..", "routes")

# Role mapping per route file
ROLE_MAP = {
    # --- Group A: Fatturazione (admin, amministrazione) ---
    "invoices.py": ("admin", "amministrazione"),
    "fatture_ricevute.py": ("admin", "amministrazione"),
    "ddt.py": ("admin", "amministrazione"),

    # --- Group B: Costi (admin, amministrazione) ---
    "cost_control.py": ("admin", "amministrazione"),
    "sal_acconti.py": ("admin", "amministrazione"),

    # --- Group C: Clienti (admin, amministrazione, ufficio_tecnico) ---
    "clients.py": ("admin", "amministrazione", "ufficio_tecnico"),

    # --- Group D: Impostazioni (admin, amministrazione) ---
    "company.py": ("admin", "amministrazione"),
    "payment_types.py": ("admin", "amministrazione"),

    # --- Group E: Commerciale (admin, amministrazione, ufficio_tecnico) ---
    "preventivi.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "preventivatore.py": ("admin", "amministrazione", "ufficio_tecnico"),

    # --- Group F: Commesse/Produzione (tutti i ruoli operativi) ---
    "commesse.py": ("admin", "amministrazione", "ufficio_tecnico", "officina"),
    "commessa_ops.py": ("admin", "amministrazione", "ufficio_tecnico", "officina"),
    "commessa_ops_common.py": ("admin", "amministrazione", "ufficio_tecnico", "officina"),
    "commesse_normative.py": ("admin", "ufficio_tecnico"),
    "produzione_ops.py": ("admin", "ufficio_tecnico", "officina"),
    "officina.py": ("admin", "ufficio_tecnico", "officina"),
    "diario_produzione.py": ("admin", "ufficio_tecnico", "officina"),
    "consegne_ops.py": ("admin", "amministrazione", "ufficio_tecnico", "officina"),
    "montaggio.py": ("admin", "ufficio_tecnico", "officina"),

    # --- Group G: Admin Only ---
    "backup.py": ("admin",),
    "migration.py": ("admin",),
    "migrazione.py": ("admin",),
    "db_cleanup.py": ("admin",),
    "admin_integrity.py": ("admin",),

    # --- Group H: Tecnico (admin, ufficio_tecnico) ---
    "certificazioni.py": ("admin", "ufficio_tecnico"),
    "cam.py": ("admin", "ufficio_tecnico"),
    "fpc.py": ("admin", "ufficio_tecnico"),
    "gate_certification.py": ("admin", "ufficio_tecnico"),
    "instruments.py": ("admin", "ufficio_tecnico"),
    "welders.py": ("admin", "ufficio_tecnico", "officina"),
    "wps.py": ("admin", "ufficio_tecnico"),
    "registro_saldatura.py": ("admin", "ufficio_tecnico", "officina"),
    "qualita.py": ("admin", "ufficio_tecnico"),
    "quality_hub.py": ("admin", "ufficio_tecnico"),
    "rilievi.py": ("admin", "ufficio_tecnico"),
    "perizia.py": ("admin", "ufficio_tecnico"),
    "distinta.py": ("admin", "ufficio_tecnico"),
    "calibrazione.py": ("admin", "ufficio_tecnico"),
    "fascicolo_tecnico.py": ("admin", "ufficio_tecnico"),
    "engine.py": ("admin", "ufficio_tecnico"),
    "controllo_finale.py": ("admin", "ufficio_tecnico"),
    "riesame_tecnico.py": ("admin", "ufficio_tecnico"),
    "report_ispezioni.py": ("admin", "ufficio_tecnico"),

    # --- Group I: Sicurezza (admin, ufficio_tecnico) ---
    "cantieri_sicurezza.py": ("admin", "ufficio_tecnico"),
    "sicurezza.py": ("admin", "ufficio_tecnico"),
    "obblighi_commessa.py": ("admin", "ufficio_tecnico"),
    "istruttoria.py": ("admin", "ufficio_tecnico"),

    # --- Group J: Archivio/Documenti (admin, amministrazione, ufficio_tecnico) ---
    "archivio.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "documenti_ops.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "company_docs.py": ("admin", "amministrazione"),
    "pacco_documenti.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "pacchetti_documentali.py": ("admin", "ufficio_tecnico"),
    "dop_frazionata.py": ("admin", "ufficio_tecnico"),
    "template_111.py": ("admin", "ufficio_tecnico"),
    "manuale.py": ("admin", "ufficio_tecnico"),

    # --- Group K: Catalogo/Magazzino (admin, amministrazione, ufficio_tecnico) ---
    "articoli.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "attrezzature.py": ("admin", "ufficio_tecnico", "officina"),
    "consumables.py": ("admin", "ufficio_tecnico", "officina"),
    "approvvigionamento.py": ("admin", "amministrazione"),
    "movimenti.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "catalogo.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "sfridi.py": ("admin", "ufficio_tecnico", "officina"),
    "voci_lavoro.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "scadenziario_manutenzioni.py": ("admin", "ufficio_tecnico"),

    # --- Group L: Committenza/Profili (admin, amministrazione, ufficio_tecnico) ---
    "committenza.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "profili_committente.py": ("admin", "amministrazione", "ufficio_tecnico"),

    # --- Group M: Dashboard/KPI (tutti i ruoli autenticati) ---
    "dashboard.py": ("admin", "amministrazione", "ufficio_tecnico", "officina"),
    "kpi_dashboard.py": ("admin", "amministrazione", "ufficio_tecnico"),

    # --- Group N: Verbali (admin, ufficio_tecnico) ---
    "verbale_posa.py": ("admin", "ufficio_tecnico"),
    "verbali_itt.py": ("admin", "ufficio_tecnico"),

    # --- Group O: Sopralluogo (admin, ufficio_tecnico) ---
    "sopralluogo.py": ("admin", "ufficio_tecnico"),

    # --- Group P: Produzione specifica ---
    "rdp.py": ("admin", "ufficio_tecnico", "officina"),
    "conto_lavoro.py": ("admin", "amministrazione", "ufficio_tecnico"),

    # --- Group Q: Audit/Activity (admin) ---
    "activity_log.py": ("admin",),
    "audits.py": ("admin", "amministrazione"),

    # --- Group R: Notifiche/Smart (tutti) ---
    "notifications.py": ("admin", "amministrazione", "ufficio_tecnico", "officina"),
    "notifiche_smart.py": ("admin", "amministrazione", "ufficio_tecnico", "officina"),
    "smart_assign.py": ("admin", "ufficio_tecnico"),
    "smistatore.py": ("admin", "amministrazione", "ufficio_tecnico"),
    "validation.py": ("admin", "ufficio_tecnico"),
}

# Files to SKIP (public, auth, special handling)
SKIP_FILES = {
    "auth.py",        # Public auth endpoints
    "vendor_api.py",  # External API callbacks
    "demo.py",        # Has its own special auth
    "team.py",        # Already has role checks
    "content_engine.py",  # Already has role checks
    "search.py",      # Broad access needed
    "onboarding.py",  # Needs special handling
    "qrcode_gen.py",  # Utility
    "__init__.py",
}


def apply_rbac_to_file(filepath: str, roles: tuple) -> dict:
    """Apply RBAC decorator to a single route file. Returns stats."""
    filename = os.path.basename(filepath)
    stats = {"file": filename, "changes": 0, "skipped": False, "error": None}

    try:
        with open(filepath, "r") as f:
            content = f.read()
    except Exception as e:
        stats["error"] = str(e)
        return stats

    # Skip if already has require_role
    if "from core.rbac import require_role" in content:
        stats["skipped"] = True
        return stats

    # Skip if no get_current_user usage
    if "get_current_user" not in content:
        stats["skipped"] = True
        return stats

    original = content

    # 1. Add require_role import after the security import line
    security_import = "from core.security import get_current_user"
    if security_import in content:
        content = content.replace(
            security_import,
            security_import + "\nfrom core.rbac import require_role",
            1  # only first occurrence
        )

    # 2. Build the role string for Depends
    role_args = ", ".join(f'"{r}"' for r in roles)
    role_depends = f"Depends(require_role({role_args}))"

    # 3. Replace Depends(get_current_user) with role-based Depends
    # Pattern: user: dict = Depends(get_current_user)
    # Also handle variations like user=Depends(get_current_user)
    pattern = r"Depends\(get_current_user\)"
    content = re.sub(pattern, role_depends, content)

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        stats["changes"] = content.count("require_role") - 1  # -1 for the import
    else:
        stats["skipped"] = True

    return stats


def main():
    results = []
    route_files = sorted(os.listdir(ROUTES_DIR))

    for filename in route_files:
        if not filename.endswith(".py"):
            continue
        if filename in SKIP_FILES:
            results.append({"file": filename, "skipped": True, "changes": 0, "error": None, "reason": "in SKIP list"})
            continue

        filepath = os.path.join(ROUTES_DIR, filename)

        if filename in ROLE_MAP:
            stats = apply_rbac_to_file(filepath, ROLE_MAP[filename])
            results.append(stats)
        else:
            results.append({"file": filename, "skipped": True, "changes": 0, "error": None, "reason": "not in ROLE_MAP"})

    # Print summary
    patched = [r for r in results if r.get("changes", 0) > 0]
    skipped = [r for r in results if r.get("skipped")]
    errors = [r for r in results if r.get("error")]

    print(f"\n=== RBAC Application Summary ===")
    print(f"Total files processed: {len(results)}")
    print(f"Files patched: {len(patched)}")
    print(f"Files skipped: {len(skipped)}")
    print(f"Errors: {len(errors)}")

    if patched:
        print(f"\nPatched files:")
        for r in patched:
            print(f"  + {r['file']} ({r['changes']} endpoints)")

    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  ! {r['file']}: {r['error']}")

    if skipped:
        print(f"\nSkipped:")
        for r in skipped:
            reason = r.get("reason", "already patched or no get_current_user")
            print(f"  - {r['file']} ({reason})")


if __name__ == "__main__":
    main()
