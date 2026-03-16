/**
 * PDF Preview Modal — genera PDF nel browser via jsPDF CDN.
 * Nessuna dipendenza npm aggiuntiva, nessuna chiamata backend.
 */
import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Eye, Download, Loader2, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../lib/utils';

function getAuthHeaders() {
    const token = localStorage.getItem('session_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

function loadScript(src) {
    return new Promise((resolve, reject) => {
        if (document.querySelector('script[src="' + src + '"]')) { resolve(); return; }
        const s = document.createElement('script');
        s.src = src;
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
    });
}

function fmtEur(v) {
    const n = parseFloat(v) || 0;
    return n.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
}
function fmtQty(v) {
    const n = parseFloat(v) || 0;
    return n.toLocaleString('it-IT', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}
function fmtDate(d) {
    if (!d) return '';
    try { return new Date(d).toLocaleDateString('it-IT'); } catch(e) { return ''; }
}

async function buildPDF(prev, company, client) {
    await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js');
    await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js');
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const co = company || {};
    const cl = client || {};
    const pageW = 210;
    const margin = 15;
    let y = 15;
    const blue = [0, 85, 255];
    const dark = [30, 41, 59];
    const gray = [100, 116, 139];
    const lightGray = [241, 245, 249];

    doc.setFillColor(...blue);
    doc.rect(0, 0, pageW, 28, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text(co.business_name || co.name || 'Steel Project Design', margin, 11);
    doc.setFontSize(7.5);
    doc.setFont('helvetica', 'normal');
    const coAddr = [co.address, co.city, co.vat_number ? 'P.IVA ' + co.vat_number : ''].filter(Boolean).join('  |  ');
    if (coAddr) doc.text(coAddr, margin, 17);
    if (co.email || co.phone) doc.text([co.email, co.phone].filter(Boolean).join('  |  '), margin, 22);

    y = 34;
    const docNum = (prev.number || '').replace('PRV-', '').replace('/', '-');
    doc.setTextColor(...dark);
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text('PREVENTIVO', margin, y);
    doc.setFontSize(11);
    doc.setTextColor(...gray);
    doc.text('N. ' + docNum, margin, y + 7);
    y += 16;

    const boxH = 28;
    doc.setFillColor(...lightGray);
    doc.roundedRect(margin, y, 90, boxH, 2, 2, 'F');
    doc.roundedRect(pageW - margin - 65, y, 65, boxH, 2, 2, 'F');
    doc.setFontSize(7);
    doc.setTextColor(...gray);
    doc.setFont('helvetica', 'bold');
    doc.text('CLIENTE', margin + 4, y + 5);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(...dark);
    const clientName = cl.business_name || prev.client_name || '-';
    doc.text(clientName.substring(0, 40), margin + 4, y + 11);
    const clAddr = [cl.address, cl.city].filter(Boolean).join(', ');
    if (clAddr) doc.text(clAddr.substring(0, 40), margin + 4, y + 17);
    if (cl.vat_number) doc.text('P.IVA ' + cl.vat_number, margin + 4, y + 23);
    const metaX = pageW - margin - 63;
    doc.setFontSize(7);
    doc.setTextColor(...gray);
    doc.setFont('helvetica', 'bold');
    doc.text('DETTAGLI', metaX, y + 5);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(...dark);
    doc.text('Data: ' + fmtDate(prev.created_at || prev.data_preventivo), metaX, y + 11);
    doc.text('Validita: ' + (prev.validity_days || 30) + ' giorni', metaX, y + 17);
    if (prev.payment_type_label) doc.text('Pag.: ' + prev.payment_type_label.substring(0, 25), metaX, y + 23);
    y += boxH + 8;

    if (prev.subject) {
        doc.setFontSize(9);
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(...dark);
        doc.text('Oggetto:', margin, y);
        doc.setFont('helvetica', 'normal');
        const subjectLines = doc.splitTextToSize(prev.subject, 130);
        doc.text(subjectLines[0] || '', margin + 20, y);
        y += 7;
    }

    const lines = prev.lines || [];
    const rows = lines.map(ln => {
        const s1 = parseFloat(ln.sconto_1 || 0);
        const s2 = parseFloat(ln.sconto_2 || 0);
        let sc = '';
        if (s1 > 0 && s2 > 0) sc = fmtQty(s1) + '%+' + fmtQty(s2) + '%';
        else if (s1 > 0) sc = fmtQty(s1) + '%';
        else if (s2 > 0) sc = fmtQty(s2) + '%';
        const desc = (ln.description || '').replace(/\n/g, ' ');
        return [ln.codice_articolo || '', desc, ln.unit || 'pz', fmtQty(ln.quantity), fmtEur(ln.unit_price), sc, fmtEur(ln.line_total), (ln.vat_rate || 22) + '%'];
    });

    doc.autoTable({
        startY: y,
        head: [['Codice', 'Descrizione', 'U.M.', 'Qta', 'Prezzo', 'Sc.', 'Importo', 'IVA']],
        body: rows,
        theme: 'grid',
        headStyles: { fillColor: blue, textColor: 255, fontStyle: 'bold', fontSize: 8, cellPadding: 3 },
        bodyStyles: { fontSize: 7.5, textColor: dark, cellPadding: 2.5 },
        alternateRowStyles: { fillColor: [248, 250, 252] },
        columnStyles: {
            0: { cellWidth: 18 }, 1: { cellWidth: 65 }, 2: { cellWidth: 12, halign: 'center' },
            3: { cellWidth: 13, halign: 'right' }, 4: { cellWidth: 22, halign: 'right' },
            5: { cellWidth: 14, halign: 'center' }, 6: { cellWidth: 22, halign: 'right' },
            7: { cellWidth: 14, halign: 'center' },
        },
        margin: { left: margin, right: margin },
    });

    y = doc.lastAutoTable.finalY + 6;
    const totals = prev.totals || {};
    const subtotal = parseFloat(totals.subtotal || 0);
    const scontoVal = parseFloat(totals.sconto_val || 0);
    const imponibile = parseFloat(totals.imponibile || subtotal);
    const iva = parseFloat(totals.total_vat || 0);
    const total = parseFloat(totals.total || 0);
    const acconto = parseFloat(totals.acconto || prev.acconto || 0);
    const daPagare = parseFloat(totals.da_pagare || (total - acconto));
    const totX = pageW - margin - 70;
    const totW = 70;
    const totRows = [
        ['Subtotale', fmtEur(subtotal)],
        ...(scontoVal > 0 ? [['Sconto ' + (totals.sconto_globale_pct || 0) + '%', '- ' + fmtEur(scontoVal)]] : []),
        ['Imponibile', fmtEur(imponibile)],
        ['IVA', fmtEur(iva)],
        ...(acconto > 0 ? [['Acconto', '- ' + fmtEur(acconto)]] : []),
    ];
    totRows.forEach(([label, value]) => {
        doc.setFillColor(...lightGray);
        doc.rect(totX, y, totW, 6.5, 'F');
        doc.setFontSize(8);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(...gray);
        doc.text(label, totX + 3, y + 4.5);
        doc.setTextColor(...dark);
        doc.text(value, totX + totW - 3, y + 4.5, { align: 'right' });
        y += 7;
    });
    doc.setFillColor(...blue);
    doc.rect(totX, y, totW, 8, 'F');
    doc.setFontSize(9);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('TOTALE', totX + 3, y + 5.5);
    doc.text(fmtEur(daPagare || total), totX + totW - 3, y + 5.5, { align: 'right' });

    if (prev.notes && prev.notes.trim()) {
        const noteY = doc.lastAutoTable.finalY + 10;
        doc.setFontSize(8);
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(...dark);
        doc.text('Note:', margin, noteY);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(...gray);
        const noteLines = doc.splitTextToSize(prev.notes, 120);
        doc.text(noteLines.slice(0, 4), margin, noteY + 6);
    }

    const iban = prev.iban || (co.bank_details && co.bank_details.iban);
    const banca = prev.banca || (co.bank_details && co.bank_details.bank_name);
    if (iban || banca) {
        const bankY = doc.internal.pageSize.height - 25;
        doc.setFillColor(...lightGray);
        doc.rect(margin, bankY, 120, 14, 'F');
        doc.setFontSize(7.5);
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(...dark);
        doc.text('Dati bancari', margin + 3, bankY + 5);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(...gray);
        if (banca) doc.text('Banca: ' + banca, margin + 3, bankY + 10);
        if (iban) doc.text('IBAN: ' + iban, margin + 3 + (banca ? 55 : 0), bankY + 10);
    }

    const footerY = doc.internal.pageSize.height - 8;
    doc.setDrawColor(220, 220, 220);
    doc.line(margin, footerY - 2, pageW - margin, footerY - 2);
    doc.setFontSize(7);
    doc.setTextColor(...gray);
    doc.setFont('helvetica', 'normal');
    doc.text(co.business_name || '', margin, footerY);
    doc.text('Preventivo ' + (prev.number || '') + ' - Pag. 1', pageW / 2, footerY, { align: 'center' });
    doc.text('NormaFacile 2.0', pageW - margin, footerY, { align: 'right' });

    return doc;
}

export function PDFPreviewModal({ open, onClose, pdfUrl, title, preventivoId }) {
    const [loading, setLoading] = useState(false);
    const [blobUrl, setBlobUrl] = useState(null);
    const [error, setError] = useState(null);

    const extractId = (url) => {
        if (!url) return null;
        const m = url.match(/\/preventivi\/([^\/]+)\/pdf/);
        return m ? m[1] : null;
    };

    const generate = useCallback(async () => {
        const id = preventivoId || extractId(pdfUrl);
        if (!id) { setError('ID preventivo non trovato'); return; }
        setLoading(true);
        setError(null);
        try {
            const headers = getAuthHeaders();
            const [prevRes, compRes] = await Promise.all([
                fetch(API_BASE + '/preventivi/' + id, { headers }),
                fetch(API_BASE + '/settings/company', { headers }),
            ]);
            if (!prevRes.ok) throw new Error('Errore caricamento dati: ' + prevRes.status);
            const prev = await prevRes.json();
            const company = compRes.ok ? await compRes.json() : {};
            let client = {};
            if (prev.client_id) {
                const cRes = await fetch(API_BASE + '/clients/' + prev.client_id, { headers });
                if (cRes.ok) client = await cRes.json();
            }
            const doc = await buildPDF(prev, company, client);
            const blob = doc.output('blob');
            if (blobUrl) URL.revokeObjectURL(blobUrl);
            setBlobUrl(URL.createObjectURL(blob));
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [pdfUrl, preventivoId]);

    useEffect(() => {
        if (open) generate();
        return () => {};
    }, [open]);

    const handleClose = () => {
        if (blobUrl) URL.revokeObjectURL(blobUrl);
        setBlobUrl(null);
        onClose();
    };

    const handleDownload = () => {
        if (!blobUrl) return;
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = (title || 'preventivo') + '.pdf';
        a.click();
    };

    return (
        <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
            <DialogContent className="sm:max-w-[900px] max-h-[95vh] flex flex-col p-0" data-testid="pdf-preview-modal">
                <DialogHeader className="px-4 py-3 border-b border-slate-200 shrink-0">
                    <div className="flex items-center justify-between w-full">
                        <DialogTitle className="text-sm font-semibold text-[#1E293B]">
                            {title || 'Anteprima PDF'}
                        </DialogTitle>
                        <Button variant="outline" size="sm" onClick={handleDownload}
                            disabled={!blobUrl} className="text-xs h-8" data-testid="btn-download-pdf-modal">
                            <Download className="h-3.5 w-3.5 mr-1" /> Scarica
                        </Button>
                    </div>
                </DialogHeader>
                <div className="flex-1 overflow-hidden bg-slate-200 flex justify-center items-center" style={{ minHeight: '70vh' }}>
                    {loading && (
                        <div className="text-center">
                            <Loader2 className="h-8 w-8 animate-spin text-[#0055FF] mx-auto mb-2" />
                            <p className="text-xs text-slate-500">Generazione PDF...</p>
                        </div>
                    )}
                    {error && !loading && (
                        <div className="text-center px-4">
                            <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                            <p className="text-sm text-red-600 mb-1">Errore generazione PDF</p>
                            <p className="text-xs text-slate-500">{error}</p>
                            <Button size="sm" className="mt-3 text-xs" onClick={generate}>Riprova</Button>
                        </div>
                    )}
                    {blobUrl && !loading && (
                        <iframe src={blobUrl} className="w-full border-0"
                            style={{ height: '75vh' }} title="PDF Preview" />
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

export function PDFPreviewButton({ pdfUrl, title, preventivoId, variant = 'outline', size = 'sm', className = '' }) {
    const [open, setOpen] = useState(false);
    return (
        <>
            <Button variant={variant} size={size} data-testid="btn-preview-pdf"
                onClick={() => setOpen(true)} className={'text-xs ' + className}>
                <Eye className="h-3.5 w-3.5 mr-1.5" /> Anteprima
            </Button>
            <PDFPreviewModal open={open} onClose={() => setOpen(false)}
                pdfUrl={pdfUrl} title={title} preventivoId={preventivoId} />
        </>
    );
}
