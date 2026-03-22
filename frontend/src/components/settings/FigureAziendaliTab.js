import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { apiRequest } from '../../lib/utils';
import { Users, Shield } from 'lucide-react';

const RUOLI_AZIENDALI = [
    { ruolo: 'DATORE_LAVORO', label: 'Datore di Lavoro', obbligatorio: true },
    { ruolo: 'RSPP', label: 'RSPP', obbligatorio: true },
    { ruolo: 'MEDICO_COMPETENTE', label: 'Medico Competente', obbligatorio: true },
    { ruolo: 'PREPOSTO_CANTIERE', label: 'Preposto di Cantiere', obbligatorio: false },
    { ruolo: 'DIRETTORE_TECNICO', label: 'Direttore Tecnico', obbligatorio: false },
];

export default function FigureAziendaliTab({ settings, setSettings }) {
    const figures = settings.figure_aziendali || [];

    useEffect(() => {
        if (figures.length === 0) {
            const defaults = RUOLI_AZIENDALI.map(r => ({
                ruolo: r.ruolo,
                label: r.label,
                nome: '',
                telefono: '',
                email: '',
            }));
            setSettings(prev => ({ ...prev, figure_aziendali: defaults }));
        }
    }, []);

    const updateFigura = (ruolo, field, value) => {
        setSettings(prev => ({
            ...prev,
            figure_aziendali: (prev.figure_aziendali || []).map(f =>
                f.ruolo === ruolo ? { ...f, [field]: value } : f
            ),
        }));
    };

    const getRuoloDef = (ruolo) => RUOLI_AZIENDALI.find(r => r.ruolo === ruolo);

    return (
        <Card className="border-gray-200">
            <CardHeader className="bg-blue-50 border-b border-gray-200">
                <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-[#0055FF]" />
                    Figure Aziendali Sicurezza
                </CardTitle>
                <CardDescription>
                    Definisci i referenti aziendali predefiniti per la sicurezza. Questi dati verranno precompilati automaticamente in ogni nuova Scheda Cantiere (POS).
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-6">
                {(figures.length > 0 ? figures : RUOLI_AZIENDALI.map(r => ({ ruolo: r.ruolo, label: r.label, nome: '', telefono: '', email: '' }))).map(fig => {
                    const def = getRuoloDef(fig.ruolo);
                    return (
                        <div key={fig.ruolo} className="p-4 rounded-lg border border-gray-200 bg-white" data-testid={`figura-${fig.ruolo}`}>
                            <div className="flex items-center gap-2 mb-3">
                                <Users className="h-4 w-4 text-slate-500" />
                                <Label className="font-semibold text-sm">{fig.label || fig.ruolo}</Label>
                                {def?.obbligatorio && <Badge className="text-[10px] bg-red-100 text-red-700">obbligatorio</Badge>}
                                {fig.nome && <Badge className="text-[10px] bg-emerald-100 text-emerald-700">compilato</Badge>}
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <div>
                                    <Label className="text-xs text-slate-500">Nome</Label>
                                    <Input
                                        data-testid={`input-figura-nome-${fig.ruolo}`}
                                        placeholder="Nome e Cognome"
                                        value={fig.nome || ''}
                                        onChange={e => updateFigura(fig.ruolo, 'nome', e.target.value)}
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs text-slate-500">Telefono</Label>
                                    <Input
                                        data-testid={`input-figura-tel-${fig.ruolo}`}
                                        placeholder="Telefono"
                                        value={fig.telefono || ''}
                                        onChange={e => updateFigura(fig.ruolo, 'telefono', e.target.value)}
                                    />
                                </div>
                                <div>
                                    <Label className="text-xs text-slate-500">Email</Label>
                                    <Input
                                        data-testid={`input-figura-email-${fig.ruolo}`}
                                        placeholder="Email"
                                        value={fig.email || ''}
                                        onChange={e => updateFigura(fig.ruolo, 'email', e.target.value)}
                                    />
                                </div>
                            </div>
                        </div>
                    );
                })}
            </CardContent>
        </Card>
    );
}
