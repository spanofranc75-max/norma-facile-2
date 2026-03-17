<Button variant="outline" onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/ddt/${ddtId}/pdf?token=${localStorage.getItem('session_token')}`, '_blank')} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 h-9 text-xs"><Eye className="h-3.5 w-3.5 mr-1.5" /> Anteprima</Button></Button>
                        <div>
                            <h1 className="font-sans text-xl font-bold text-[#1E293B]">{isNew ? 'Nuovo DDT' : 'Modifica DDT'}</h1>
                            <div className="flex items-center gap-2 mt-0.5">
                                {ddtInfo.number && <span className="text-xs font-mono text-[#0055FF]">{ddtInfo.number}</span>}
                                <Badge className={`${TYPE_COLORS[form.ddt_type]} text-[10px]`}>{TYPE_OPTIONS.find(t => t.value === form.ddt_type)?.label}</Badge>
                                {!isNew && <Badge className="bg-slate-100 text-slate-700 text-[10px]">{STATUS_LABELS[ddtInfo.status]}</Badge>}
                                {ddtInfo.commessa_id && (
                                    <button
                                        data-testid="ddt-editor-commessa-link"
                                        className="inline-flex items-center gap-1 text-[10px] font-medium text-[#0055FF] bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5 hover:bg-blue-100 transition-colors"
                                        onClick={() => navigate(`/commesse/${ddtInfo.commessa_id}`)}
                                    >
                                        Commessa {ddtInfo.commessa_numero || ''}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        {!isNew && <Button data-testid="btn-download-pdf" variant="outline" onClick={handleDownloadPdf} className="border-[#0055FF] text-[#0055FF] hover:bg-blue-50 h-9 text-xs"><FileDown className="h-3.5 w-3.5 mr-1.5" /> PDF</Button>}
                        {!isNew && <Button variant="outline" onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/ddt/${ddtId}/pdf?token=${localStorage.getItem('session_token')}`, '_blank')} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 h-9 text-xs"><Eye className="h-3.5 w-3.5 mr-1.5" /> Anteprima</Button>}
                        {!isNew && (
                            <Button
                                type="button"
                                variant="outline"
                                data-testid="btn-send-email-ddt"
                                onClick={() => setEmailPreviewOpen(true)}
                                className="border-violet-400 text-violet-600 hover:bg-violet-50 h-9 text-xs"
                            >
                                <Mail className="h-3.5 w-3.5 mr-1" /> Email
                            </Button>
                        )}
                        {!isNew && ddtInfo.status !== 'fatturato' && !ddtInfo.converted_to && (
                            <Button data-testid="btn-convert-invoice" variant="outline" onClick={handleConvertToInvoice} disabled={converting} className="border-amber-500 text-amber-600 hover:bg-amber-50 h-9 text-xs">
                                <ArrowRightLeft className="h-3.5 w-3.5 mr-1.5" /> {converting ? 'Conversione...' : 'Converti in Fattura'}
                            </Button>
                        )}
                        {!isNew && ddtInfo.status === 'fatturato' && ddtInfo.converted_to && (
                            <Button data-testid="btn-go-to-invoice" variant="outline" onClick={() => navigate(`/invoices/${ddtInfo.converted_to}`)} className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 h-9 text-xs">
                                <ArrowRightLeft className="h-3.5 w-3.5 mr-1.5" /> Vai alla Fattura
                            </Button>
                        )}
                        <Button data-testid="btn-save-ddt" onClick={handleSave} disabled={saving} className="bg-[#0055FF] text-white hover:bg-[#0044CC] h-9 text-xs"><Save className="h-3.5 w-3.5 mr-1.5" /> {saving ? 'Salvataggio...' : 'Salva'}</Button>
                    </div>
                </div>

                {/* Main Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
                    {/* ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Left Sidebar ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ */}
                    <div className="space-y-3">
                        <Card className="border-gray-200">
                            <CardContent className="p-4 space-y-3">
                                <div>
                                    <Label className="text-xs">Tipo DDT</Label>
                                    <Select value={form.ddt_type} onValueChange={handleTypeChange}>
                                        <SelectTrigger data-testid="select-ddt-type" className="h-9"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {TYPE_OPTIONS.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Cliente / Fornitore</Label>
                                    <Select value={form.client_id || '__none__'} onValueChange={v => handleClientChange(v === '__none__' ? '' : v)}>
                                        <SelectTrigger data-testid="select-client" className="h-9"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">-- Nessuno --</SelectItem>
                                            {clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.business_name}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <Label className="text-xs">Oggetto</Label>
                                    <Input data-testid="input-subject" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} placeholder="Consegna materiale..." className="h-9 text-sm" />
                                </div>
                                <div>
                                    <Label className="text-xs">Riferimento</Label>
                                    <Input value={form.riferimento} onChange={e => setForm(f => ({ ...f, riferimento: e.target.value }))} placeholder="Rif. ordine..." className="h-8 text-xs" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-gray-200">
                            <div className="flex border-b border-slate-200">
                                {SIDEBAR_TABS.map(t => (
                                    <button key={t.key} onClick={() => setSidebarTab(t.key)} className={`flex-1 py-2 text-[10px] font-medium text-center border-b-2 transition-colors ${sidebarTab === t.key ? 'border-[#0055FF] text-[#0055FF]' : 'border-transparent text-slate-500'}`}>
                                        <t.icon className="h-3.5 w-3.5 mx-auto mb-0.5" />{t.label}
                                    </button>
                                ))}
                            </div>
                            <CardContent className="p-3 space-y-2.5">
                                {sidebarTab === 'trasporto' && (
                                    <div className="space-y-2.5">
                                        <div><Label className="text-xs">Causale Trasporto</Label>
                                            <Select value={form.causale_trasporto} onValueChange={v => setForm(f => ({ ...f, causale_trasporto: v }))}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                <SelectContent>{CAUSALI.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                                            </Select>
                                        </div>
                                        <div><Label className="text-xs">Aspetto Beni</Label>
                                            <Select value={form.aspetto_beni || '__none__'} onValueChange={v => setForm(f => ({ ...f, aspetto_beni: v === '__none__' ? '' : v }))}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                                <SelectContent><SelectItem value="__none__">--</SelectItem>{ASPETTI.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
                                            </Select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div><Label className="text-xs">Porto</Label>
                                                <Select value={form.porto} onValueChange={v => setForm(f => ({ ...f, porto: v }))}>
                                                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                    <SelectContent>{PORTI.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
                                                </Select>
                                            </div>
                                            <div><Label className="text-xs">Mezzo</Label>
                                                <Select value={form.mezzo_trasporto} onValueChange={v => setForm(f => ({ ...f, mezzo_trasporto: v }))}>
                                                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                    <SelectContent>{MEZZI.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                                                </Select>
                                            </div>
                                        </div>
                                        <div><Label className="text-xs">Vettore</Label><Input value={form.vettore} onChange={e => setForm(f => ({ ...f, vettore: e.target.value }))} className="h-8 text-xs" /></div>
                                        <div><Label className="text-xs">Data/Ora Trasporto</Label><Input value={form.data_ora_trasporto} onChange={e => setForm(f => ({ ...f, data_ora_trasporto: e.target.value }))} className="h-8 text-xs" placeholder="27/02/2026 16:00" /></div>
                                        <Separator />
                                        <div className="grid grid-cols-3 gap-2">
                                            <div><Label className="text-xs">Colli</Label><Input type="number" value={form.num_colli} onChange={e => setForm(f => ({ ...f, num_colli: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                            <div><Label className="text-xs">P. Lordo</Label><Input type="number" step="0.1" value={form.peso_lordo_kg} onChange={e => setForm(f => ({ ...f, peso_lordo_kg: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                            <div><Label className="text-xs">P. Netto</Label><Input type="number" step="0.1" value={form.peso_netto_kg} onChange={e => setForm(f => ({ ...f, peso_netto_kg: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                        </div>
                                    </div>
                                )}
                                {sidebarTab === 'destinazione' && (
                                    <div className="space-y-2">
                                        <div><Label className="text-xs">Ragione Sociale</Label><Input value={form.destinazione.ragione_sociale} onChange={e => updateDest('ragione_sociale', e.target.value)} className="h-8 text-xs" /></div>
                                        <div><Label className="text-xs">Indirizzo</Label><Input value={form.destinazione.indirizzo} onChange={e => updateDest('indirizzo', e.target.value)} className="h-8 text-xs" /></div>
                                        <div className="grid grid-cols-3 gap-2">
                                            <div><Label className="text-xs">CAP</Label><Input value={form.destinazione.cap} onChange={e => updateDest('cap', e.target.value)} className="h-8 text-xs" maxLength={5} /></div>
                                            <div><Label className="text-xs">LocalitÃÂÃÂÃÂÃÂ </Label><Input value={form.destinazione.localita} onChange={e => updateDest('localita', e.target.value)} className="h-8 text-xs" /></div>
                                            <div><Label className="text-xs">Prov.</Label><Input value={form.destinazione.provincia} onChange={e => updateDest('provincia', e.target.value.toUpperCase())} className="h-8 text-xs" maxLength={2} /></div>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div><Label className="text-xs">Telefono</Label><Input value={form.destinazione.telefono} onChange={e => updateDest('telefono', e.target.value)} className="h-8 text-xs" /></div>
                                            <div><Label className="text-xs">Cellulare</Label><Input value={form.destinazione.cellulare} onChange={e => updateDest('cellulare', e.target.value)} className="h-8 text-xs" /></div>
                                        </div>
                                    </div>
                                )}
                                {sidebarTab === 'pagamento' && (
                                    <div className="space-y-2.5">
                                        <div><Label className="text-xs">Condizioni Pagamento</Label>
                                            <Select value={form.payment_type_id || '__none__'} onValueChange={handlePaymentTypeChange}>
                                                <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Seleziona..." /></SelectTrigger>
                                                <SelectContent><SelectItem value="__none__">-- Nessuno --</SelectItem>{paymentTypes.map(pt => <SelectItem key={pt.payment_type_id} value={pt.payment_type_id}><span className="font-mono text-[10px] mr-1">{pt.codice}</span> {pt.descrizione}</SelectItem>)}</SelectContent>
                                            </Select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div><Label className="text-xs">Sconto Globale %</Label><Input type="number" step="0.1" value={form.sconto_globale} onChange={e => setForm(f => ({ ...f, sconto_globale: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                            <div><Label className="text-xs">Acconto</Label><Input type="number" step="0.01" value={form.acconto} onChange={e => setForm(f => ({ ...f, acconto: e.target.value }))} className="h-8 text-xs font-mono" /></div>
                                        </div>
                                        <label className="flex items-center gap-2 text-xs cursor-pointer">
                                            <Checkbox checked={form.stampa_prezzi} onCheckedChange={v => setForm(f => ({ ...f, stampa_prezzi: v }))} />
                                            <span>Stampa prezzi in PDF</span>
                                        </label>
                                    </div>
                                )}
                                {sidebarTab === 'note' && (
                                    <div><Label className="text-xs">Note</Label><Textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={6} className="text-xs" /></div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Right Content ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ */}
                    <div className="space-y-4">
                        {/* Lines Table */}
                        <Card className="border-gray-200">
                            <CardHeader className="bg-[#1E293B] py-2.5 px-4 rounded-t-lg flex flex-row items-center justify-between">
                                <CardTitle className="text-xs font-semibold text-white">Dettaglio Righe</CardTitle>
                                <Button data-testid="btn-add-line" size="sm" variant="ghost" onClick={addLine} className="text-white hover:text-blue-200 h-7 text-xs"><Plus className="h-3 w-3 mr-1" /> Aggiungi</Button>
                            </CardHeader>
                            <CardContent className="p-0 overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead className="w-7 text-[10px]">#</TableHead>
                                            <TableHead className="w-20 text-[10px]">Codice</TableHead>
                                            <TableHead className="min-w-[160px] text-[10px]">Descrizione</TableHead>
                                            <TableHead className="w-14 text-[10px]">UdM</TableHead>
                                            <TableHead className="w-16 text-right text-[10px]">Q.tÃÂÃÂÃÂÃÂ </TableHead>
                                            <TableHead className="w-20 text-right text-[10px]">Prezzo</TableHead>
                                            <TableHead className="w-14 text-right text-[10px]">Sc.1%</TableHead>
                                            <TableHead className="w-14 text-right text-[10px]">Sc.2%</TableHead>
                                            <TableHead className="w-20 text-right text-[10px]">Totale</TableHead>
                                            <TableHead className="w-14 text-[10px]">IVA</TableHead>
                                            <TableHead className="w-8"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {form.lines.map((l, i) => (
                                            <TableRow key={l.line_id} data-testid={`line-${i}`}>
                                                <TableCell className="text-[10px] text-slate-400 font-mono">{i + 1}</TableCell>
                                                <TableCell><Input value={l.codice_articolo} onChange={e => updateLine(i, 'codice_articolo', e.target.value)} className="h-7 text-xs font-mono" /></TableCell>
                                                <TableCell><AutoExpandTextarea value={l.description} onChange={e => updateLine(i, 'description', e.target.value)} className="text-xs" /></TableCell>
                                                <TableCell>
                                                    <Select value={l.unit} onValueChange={v => updateLine(i, 'unit', v)}>
                                                        <SelectTrigger className="h-7 text-[10px] w-14"><SelectValue /></SelectTrigger>
                                                        <SelectContent>
                                                            {['pz', 'm', 'mq', 'kg', 'h', 'corpo'].map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                                                        </SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell><Input type="number" value={l.quantity} onChange={e => updateLine(i, 'quantity', e.target.value)} className="h-7 text-xs text-right font-mono" /></TableCell>
                                                <TableCell><Input type="number" step="0.01" value={l.unit_price} onChange={e => updateLine(i, 'unit_price', e.target.value)} className="h-7 text-xs text-right font-mono text-red-600 font-semibold" /></TableCell>
                                                <TableCell><Input type="number" step="0.1" value={l.sconto_1} onChange={e => updateLine(i, 'sconto_1', e.target.value)} className="h-7 text-[10px] text-right font-mono w-14" /></TableCell>
                                                <TableCell><Input type="number" step="0.1" value={l.sconto_2} onChange={e => updateLine(i, 'sconto_2', e.target.value)} className="h-7 text-[10px] text-right font-mono w-14" /></TableCell>
                                                <TableCell className="text-right font-mono text-xs font-semibold text-[#0055FF]">{fmtEur(lineTotal(l))}</TableCell>
                                                <TableCell>
                                                    <Select value={l.vat_rate} onValueChange={v => updateLine(i, 'vat_rate', v)}>
                                                        <SelectTrigger className="h-7 text-[10px] w-14"><SelectValue /></SelectTrigger>
                                                        <SelectContent>{['22', '10', '4', '0'].map(r => <SelectItem key={r} value={r}>{r}%</SelectItem>)}</SelectContent>
                                                    </Select>
                                                </TableCell>
                                                <TableCell>{form.lines.length > 1 && <button onClick={() => removeLine(i)} className="p-1 text-slate-400 hover:text-red-500"><Trash2 className="h-3 w-3" /></button>}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>

                        {/* Totals */}
                        <Card className="border-gray-200" data-testid="totals-card">
                            <CardContent className="p-4">
                                <div className="flex justify-end">
                                    <div className="w-64 space-y-1.5">
                                        <TotalRow label="Totale senza IVA" value={fmtEur(subtotal)} />
                                        {parseFloat(form.sconto_globale) > 0 && <TotalRow label={`Sconto ${form.sconto_globale}%`} value={`-${fmtEur(scontoVal)}`} className="text-red-500" />}
                                        <TotalRow label="Imponibile" value={fmtEur(imponibile)} />
                                        <TotalRow label="Totale IVA" value={fmtEur(totalVat)} />
                                        <Separator />
                                        <div className="flex justify-between items-center pt-1">
                                            <span className="text-sm font-bold text-[#1E293B]">TOTALE</span>
                                            <span className="font-mono text-lg font-bold text-[#0055FF]">{fmtEur(totale)}</span>
                                        </div>
                                        {parseFloat(form.acconto) > 0 && <TotalRow label="Acconto" value={`-${fmtEur(form.acconto)}`} className="text-amber-600" />}
                                        {parseFloat(form.acconto) > 0 && (
                                            <div className="flex justify-between items-center bg-slate-50 -mx-4 px-4 py-2 rounded-b-lg">
                                                <span className="text-sm font-bold text-[#1E293B]">DA PAGARE</span>
                                                <span className="font-mono text-lg font-bold text-emerald-600">{fmtEur(daPagare)}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
            <EmailPreviewDialog
                open={emailPreviewOpen}
                onOpenChange={setEmailPreviewOpen}
                previewUrl={`/api/ddt/${ddtId}/preview-email`}
                sendUrl={`/api/ddt/${ddtId}/send-email`}
            />
        </DashboardLayout>
    );
}

function TotalRow({ label, value, className = '' }) {
    return (
        <div className="flex justify-between text-xs">
            <span className="text-slate-500">{label}</span>
            <span className={`font-mono font-medium ${className}`}>{value}</span>
        </div>
    );
}
