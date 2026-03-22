"""
Motore di Applicabilita Condizionale
======================================
Analizza le risposte utente alle domande residue dell'istruttoria
e determina quali requisiti, documenti e controlli sono applicabili.

4 rami ad alto impatto:
1. Saldatura   -> WPS, WPQR, qualifica, VT, registro
2. Zincatura   -> documenti subfornitore, DDT terzista
3. Commessa Mista -> blocco conferma, segmentazione normativa
4. Montaggio   -> documenti/controlli posa

Reason codes strutturati per audit, analytics e Fase 2/3.
"""

import logging

logger = logging.getLogger(__name__)


# ─── Reason Codes ───
NO_WELDING = "NO_WELDING"
NO_GALVANIZING = "NO_GALVANIZING"
EXTERNAL_GALVANIZING = "EXTERNAL_GALVANIZING"
NO_INSTALLATION = "NO_INSTALLATION"
MIXED_ORDER_REQUIRES_SEGMENTATION = "MIXED_ORDER_REQUIRES_SEGMENTATION"


def _detect_category(question_text: str):
    t = question_text.lower()
    if any(kw in t for kw in ['saldatura', 'saldare', 'saldato', 'giunzione']):
        return 'saldatura'
    if any(kw in t for kw in ['protezione superficial', 'zincatura', 'verniciatura',
                               'trattamento superficial', 'rivestimento']):
        return 'zincatura'
    if any(kw in t for kw in ['montaggio', 'installazione', 'cantiere', 'posa in opera']):
        return 'montaggio'
    if any(kw in t for kw in ['mista', 'normativa mista', 'classificazione diversa']):
        return 'commessa_mista'
    return None


def _parse_answer(answer_text: str, category: str) -> str:
    """Returns: positive | negative | external | pending"""
    t = answer_text.lower().strip()
    if not t:
        return 'pending'

    if category == 'saldatura':
        if any(kw in t for kw in ['non previst', 'bullonatura', 'bullonata', 'nessuna saldatura']):
            return 'negative'
        if t in ('no', 'no.'):
            return 'negative'
        if any(kw in t for kw in ['sì', 'si', 'officina', 'terzi', 'previst']):
            return 'positive'
        if 'verificare' in t or 'definire' in t:
            return 'pending'
        return 'positive'

    if category == 'zincatura':
        # Check external FIRST (has priority over negative because "esterno" contains "no")
        if any(kw in t for kw in ['esterna', 'terzi', 'subfornitore', 'terzista', 'affidato a terzi']):
            return 'external'
        if any(kw in t for kw in ['nessun trattamento', 'non previst']):
            return 'negative'
        if t in ('no', 'no.'):
            return 'negative'
        if any(kw in t for kw in ['a caldo', 'a freddo', 'verniciatura', 'industriale']):
            return 'positive'
        if 'definire' in t or 'verificare' in t:
            return 'pending'
        return 'positive'

    if category == 'montaggio':
        # Check positive/external FIRST to avoid "no" matching in "esterno"/"interno"
        if any(kw in t for kw in ['sì', 'si', 'inclusa', 'cantiere', 'installazione']):
            return 'positive'
        if any(kw in t for kw in ['terzi', 'affidato']):
            return 'external'
        if any(kw in t for kw in ['non previsto', 'non prevista', 'solo officina', 'solo assemblaggio']):
            return 'negative'
        if t in ('no', 'no.'):
            return 'negative'
        if 'verificare' in t or 'definire' in t:
            return 'pending'
        return 'positive'

    if category == 'commessa_mista':
        if any(kw in t for kw in ['sì', 'si', 'mista']):
            return 'positive'
        if any(kw in t for kw in ['no', 'non', 'unica']):
            return 'negative'
        return 'pending'

    return 'pending'


def calcola_applicabilita(domande_residue: list, risposte_utente: dict) -> dict:
    """
    Calcola lo stato di applicabilita basato sulle risposte utente.

    Returns dict con:
      decisioni, items_non_applicabili, items_condizionali,
      blocchi_conferma, riepilogo
    """
    decisioni = {}
    for idx, domanda in enumerate(domande_residue or []):
        categoria = _detect_category(domanda.get('domanda', ''))
        if not categoria:
            continue

        risposta_obj = risposte_utente.get(str(idx), {})
        risposta_text = (risposta_obj.get('risposta', '')
                         if isinstance(risposta_obj, dict)
                         else str(risposta_obj))

        stato = _parse_answer(risposta_text, categoria)
        decisioni[categoria] = {
            'stato': stato,
            'risposta': risposta_text,
            'domanda_idx': idx,
        }

    items_non_applicabili = []
    items_condizionali = []
    blocchi_conferma = []
    riepilogo = {}

    # ── Rule 1: Saldatura ──
    sald = decisioni.get('saldatura', {})
    sald_stato = sald.get('stato')
    if sald_stato == 'negative':
        riepilogo['saldatura'] = 'Non prevista'
        for nome in ['WPS', 'WPQR', 'Qualifica saldatori',
                     'VT saldature', 'Registro saldatura']:
            items_non_applicabili.append({
                'nome': nome,
                'reason_code': NO_WELDING,
                'reason_text': 'Non applicabile: nessuna saldatura prevista',
                'categoria': 'saldatura',
            })
    elif sald_stato == 'positive':
        riepilogo['saldatura'] = 'Prevista'
    elif sald_stato == 'pending':
        riepilogo['saldatura'] = 'Da confermare'

    # ── Rule 2: Zincatura ──
    zinc = decisioni.get('zincatura', {})
    zinc_stato = zinc.get('stato')
    if zinc_stato == 'negative':
        riepilogo['zincatura'] = 'Non prevista'
        for nome in ['Certificato zincatura', 'Controllo trattamento superficiale']:
            items_non_applicabili.append({
                'nome': nome,
                'reason_code': NO_GALVANIZING,
                'reason_text': 'Non applicabile: nessun trattamento superficiale previsto',
                'categoria': 'zincatura',
            })
    elif zinc_stato == 'external':
        riepilogo['zincatura'] = 'Esterna (terzista)'
        for nome in ['Documentazione subfornitore', 'DDT verso terzista',
                     'Certificato trattamento esterno']:
            items_condizionali.append({
                'nome': nome,
                'reason_code': EXTERNAL_GALVANIZING,
                'reason_text': 'Richiesto: trattamento affidato a terzista',
                'categoria': 'zincatura',
            })
    elif zinc_stato == 'positive':
        riepilogo['zincatura'] = 'Prevista (interna)'
    elif zinc_stato == 'pending':
        riepilogo['zincatura'] = 'Da confermare'

    # ── Rule 3: Commessa mista (priorita massima per blocco) ──
    mista = decisioni.get('commessa_mista', {})
    mista_stato = mista.get('stato')
    if mista_stato == 'positive':
        riepilogo['commessa_mista'] = 'Si — richiede segmentazione'
        blocchi_conferma.append({
            'tipo': MIXED_ORDER_REQUIRES_SEGMENTATION,
            'messaggio': ('La commessa non puo essere confermata come blocco unico. '
                          'E necessaria la segmentazione normativa tra le parti '
                          'EN 1090, EN 13241 e/o Generiche.'),
            'bloccante': True,
        })
    elif mista_stato == 'negative':
        riepilogo['commessa_mista'] = 'No — normativa unica'
    elif mista_stato == 'pending':
        riepilogo['commessa_mista'] = 'Da confermare'

    # ── Rule 4: Montaggio ──
    mont = decisioni.get('montaggio', {})
    mont_stato = mont.get('stato')
    if mont_stato == 'negative':
        riepilogo['montaggio'] = 'Non previsto'
        for nome in ['Piano montaggio', 'Documenti posa in opera',
                     'POS cantiere', 'Controllo posa', 'Ispezione cantiere']:
            items_non_applicabili.append({
                'nome': nome,
                'reason_code': NO_INSTALLATION,
                'reason_text': 'Non applicabile: montaggio/installazione non previsto',
                'categoria': 'montaggio',
            })
    elif mont_stato == 'positive':
        riepilogo['montaggio'] = 'Previsto (inclusa installazione)'
    elif mont_stato == 'external':
        riepilogo['montaggio'] = 'Affidato a terzi'
    elif mont_stato == 'pending':
        riepilogo['montaggio'] = 'Da confermare'

    logger.info(
        f"[APPLICABILITA] Riepilogo: {riepilogo}, "
        f"Non applicabili: {len(items_non_applicabili)}, "
        f"Condizionali: {len(items_condizionali)}, "
        f"Blocchi: {len(blocchi_conferma)}"
    )

    return {
        'decisioni': decisioni,
        'items_non_applicabili': items_non_applicabili,
        'items_condizionali': items_condizionali,
        'blocchi_conferma': blocchi_conferma,
        'riepilogo': riepilogo,
    }


# ──────────────────────────────────────────────────────
# P0.25 — Domande Contestuali Dinamiche
# ──────────────────────────────────────────────────────

REGOLE_DOMANDE_CONTESTUALI = [
    # ── Zincatura esterna ──
    {
        'id': 'ctx_zinc_01',
        'parent_category': 'zincatura',
        'triggered_by_stato': 'external',
        'domanda': 'Nome del terzista per la zincatura?',
        'trigger_reason': 'Comparsa perché hai indicato zincatura esterna',
        'opzioni': [],
        'impatto': 'medio',
    },
    {
        'id': 'ctx_zinc_02',
        'parent_category': 'zincatura',
        'triggered_by_stato': 'external',
        'domanda': 'Per la zincatura esterna, quale evidenza/documentazione va richiesta?',
        'trigger_reason': 'Comparsa perché hai indicato zincatura esterna',
        'opzioni': [
            'Conformita trattamento secondo EN ISO 1461',
            'Documentazione generica del terzista',
            'Da definire',
        ],
        'impatto': 'alto',
    },
    # ── Saldatura presente ──
    {
        'id': 'ctx_sald_01',
        'parent_category': 'saldatura',
        'triggered_by_stato': 'positive',
        'domanda': 'Saldatura interna o affidata a terzi?',
        'trigger_reason': 'Comparsa perché hai confermato la presenza di saldatura',
        'opzioni': ['Interna', 'Affidata a terzi', 'Mista (interna + terzi)'],
        'impatto': 'alto',
    },
    {
        'id': 'ctx_sald_02',
        'parent_category': 'saldatura',
        'triggered_by_stato': 'positive',
        'domanda': 'Processo di saldatura prevalente?',
        'trigger_reason': 'Comparsa perché hai confermato la presenza di saldatura',
        'opzioni': ['135 (MIG/MAG)', '141 (TIG)', '111 (Elettrodo)', 'Da confermare'],
        'impatto': 'medio',
    },
    # ── Montaggio confermato ──
    {
        'id': 'ctx_mont_01',
        'parent_category': 'montaggio',
        'triggered_by_stato': 'positive',
        'domanda': 'Montaggio gestito internamente o affidato?',
        'trigger_reason': 'Comparsa perché hai confermato il montaggio in cantiere',
        'opzioni': ['Interno', 'Affidato a terzi'],
        'impatto': 'medio',
    },
    {
        'id': 'ctx_mont_02',
        'parent_category': 'montaggio',
        'triggered_by_stato': 'positive',
        'domanda': 'Sono richiesti documenti/controlli di posa in opera?',
        'trigger_reason': 'Comparsa perché hai confermato il montaggio in cantiere',
        'opzioni': ['Si', 'No', 'Da verificare'],
        'impatto': 'medio',
    },
]


def genera_domande_contestuali(
    domande_residue: list,
    risposte_utente: dict,
    domande_contestuali_esistenti: list | None = None,
) -> list:
    """
    Genera domande contestuali basate sulle risposte alle domande base.

    - Se il trigger e attivo → domanda active + visible
    - Se il trigger non vale piu ma c'era una risposta → stale (non cancellata)
    - Se il trigger non vale e non c'era risposta → inactive + hidden
    - Risposte esistenti preservate sempre
    """
    # Compute decisions from base answers
    decisioni = {}
    for idx, domanda in enumerate(domande_residue or []):
        categoria = _detect_category(domanda.get('domanda', ''))
        if not categoria:
            continue
        risposta_obj = risposte_utente.get(str(idx), {})
        risposta_text = (
            risposta_obj.get('risposta', '')
            if isinstance(risposta_obj, dict)
            else str(risposta_obj)
        )
        stato = _parse_answer(risposta_text, categoria)
        decisioni[categoria] = {'stato': stato, 'domanda_idx': idx}

    # Index existing contextual questions by ID
    existing_map = {}
    for q in (domande_contestuali_esistenti or []):
        existing_map[q['id']] = q

    result = []
    for rule in REGOLE_DOMANDE_CONTESTUALI:
        cat = rule['parent_category']
        triggered_by = rule['triggered_by_stato']
        decisione = decisioni.get(cat, {})

        should_be_active = decisione.get('stato') == triggered_by
        prev = existing_map.get(rule['id'])
        had_answer = bool(prev and prev.get('risposta'))

        q = {
            'id': rule['id'],
            'parent_category': rule['parent_category'],
            'parent_domanda_idx': decisione.get('domanda_idx'),
            'triggered_by_stato': triggered_by,
            'triggered_by_answer': decisione.get('stato'),
            'trigger_reason': rule['trigger_reason'],
            'domanda': rule['domanda'],
            'opzioni': rule['opzioni'],
            'impatto': rule['impatto'],
            'active': should_be_active,
            'stale': had_answer and not should_be_active,
            'visible': should_be_active,
            # Preserve existing answer data
            'risposta': prev.get('risposta') if prev else None,
            'risposto_da': prev.get('risposto_da') if prev else None,
            'risposto_da_nome': prev.get('risposto_da_nome') if prev else None,
            'risposto_il': prev.get('risposto_il') if prev else None,
        }
        result.append(q)

    n_active = sum(1 for q in result if q['active'])
    n_stale = sum(1 for q in result if q['stale'])
    logger.info(
        f"[DOMANDE_CTX] Generato {len(result)} domande contestuali: "
        f"{n_active} attive, {n_stale} stale"
    )
    return result
