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
        if any(kw in t for kw in ['no', 'non previst', 'bullonatura', 'bullonata', 'nessuna saldatura']):
            return 'negative'
        if any(kw in t for kw in ['sì', 'si', 'officina', 'terzi', 'previst']):
            return 'positive'
        if 'verificare' in t or 'definire' in t:
            return 'pending'
        return 'positive'

    if category == 'zincatura':
        if any(kw in t for kw in ['nessun trattamento', 'non previst', 'no']):
            return 'negative'
        if any(kw in t for kw in ['esterna', 'terzi', 'subfornitore', 'terzista', 'affidato a terzi']):
            return 'external'
        if any(kw in t for kw in ['a caldo', 'a freddo', 'verniciatura', 'industriale']):
            return 'positive'
        if 'definire' in t or 'verificare' in t:
            return 'pending'
        return 'positive'

    if category == 'montaggio':
        if any(kw in t for kw in ['no', 'non previsto', 'non prevista',
                                   'solo officina', 'solo assemblaggio']):
            return 'negative'
        if any(kw in t for kw in ['sì', 'si', 'inclusa', 'cantiere', 'installazione']):
            return 'positive'
        if any(kw in t for kw in ['terzi', 'affidato']):
            return 'external'
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
