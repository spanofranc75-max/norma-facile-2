/**
 * ConfrontoPreventivi — Report di confronto AI vs Manuale.
 * Mostra delta per voce, scostamento percentuale, confidence score.
 */
import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
    ArrowLeft, ArrowUpRight, ArrowDownRight, Minus, Target,
    Scale, TrendingUp, Clock, Weight, Loader2, BarChart3,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const fmtEur = (v) => typeof v === 'number' ? v.toLocaleString('it-IT', { style: 'currency', currency: 'EUR' }) : '-';
const fmtNum = (v, d = 1) => typeof v === 'number' ? v.toLocaleString('it-IT', { minimumFractionDigits: d, maximumFractionDigits: d }) : '-';

function DeltaIcon({ val }) {
    if (val > 2) return <ArrowUpRight className="w-4 h-4 text-red-400" />;
    if (val < -2) return <ArrowDownRight className="w-4 h-4 text-emerald-400" />;
    return <Minus className="w-4 h-4 text-zinc-500" />;
}

function DeltaBadge({ pct }) {
    if (!pct && pct !== 0) return null;
    const abs = Math.abs(pct);
    let color = 'bg-zinc-700 text-zinc-300';
    if (abs > 30) color = 'bg-red-900/50 text-red-300';
    else if (abs > 15) color = 'bg-amber-900/50 text-amber-300';
    else if (abs > 5) color = 'bg-blue-900/50 text-blue-300';
    else color = 'bg-emerald-900/50 text-emerald-300';
    return <span className={`px-2 py-0.5 rounded text-xs font-mono ${color}`}>{pct > 0 ? '+' : ''}{fmtNum(pct)}%</span>;
}

function ConfidenceGauge({ score, giudizio }) {
    const radius = 60;
    const circumference = Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    let color = '#ef4444';
    if (score >= 85) color = '#10b981';
    else if (score >= 70) color = '#3b82f6';
    else if (score >= 55) color = '#f59e0b';

    return (
        <div className="flex flex-col items-center gap-2" data-testid="confidence-gauge">
            <svg width="140" height="80" viewBox="0 0 140 80">
                <path d="M 10 75 A 60 60 0 0 1 130 75" fill="none" stroke="#27272a" strokeWidth="10" strokeLinecap="round" />
                <path d="M 10 75 A 60 60 0 0 1 130 75" fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
                    strokeDasharray={circumference} strokeDashoffset={offset} style={{ transition: 'stroke-dashoffset 1s ease' }} />
                <text x="70" y="55" textAnchor="middle" fill={color} fontSize="28" fontWeight="bold">{score}</text>
                <text x="70" y="72" textAnchor="middle" fill="#a1a1aa" fontSize="11">/100</text>
            </svg>
            <span className="text-sm font-medium" style={{ color }}>{giudizio}</span>
        </div>
    );
}

function CategoryRow({ label, icon: Icon, data }) {
    return (
        <div className="grid grid-cols-5 gap-2 items-center py-2 border-b border-zinc-800 last:border-0">
            <div className="flex items-center gap-2 col-span-1">
                {Icon && <Icon className="w-4 h-4 text-zinc-500" />}
                <span className="text-sm text-zinc-300">{label}</span>
            </div>
            <div className="text-right text-sm font-mono text-blue-300">{fmtEur(data?.ai)}</div>
            <div className="text-right text-sm font-mono text-amber-300">{fmtEur(data?.manuale)}</div>
            <div className="text-right text-sm font-mono flex items-center justify-end gap-1">
                <DeltaIcon val={data?.delta_pct} />
                <span className={data?.delta > 0 ? 'text-red-400' : data?.delta < 0 ? 'text-emerald-400' : 'text-zinc-400'}>
                    {data?.delta > 0 ? '+' : ''}{fmtEur(data?.delta)}
                </span>
            </div>
            <div className="text-right"><DeltaBadge pct={data?.delta_pct} /></div>
        </div>
    );
}

export default function ConfrontoPreventivi() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [prevList, setPrevList] = useState([]);
    const [aiId, setAiId] = useState(searchParams.get('ai') || '');
    const [manId, setManId] = useState(searchParams.get('man') || '');

    useEffect(() => {
        apiRequest('/preventivi/').then(r => {
            if (r && Array.isArray(r.preventivi)) setPrevList(r.preventivi);
            else if (r && Array.isArray(r)) setPrevList(r);
        }).catch(() => {});
    }, []);

    useEffect(() => {
        if (aiId && manId) runConfronto();
    }, []); // eslint-disable-line

    async function runConfronto() {
        if (!aiId || !manId) { toast.error('Seleziona entrambi i preventivi'); return; }
        setLoading(true);
        try {
            const res = await apiRequest('/preventivatore/confronta', {
                method: 'POST',
                body: JSON.stringify({ preventivo_ai_id: aiId, preventivo_manuale_id: manId }),
            });
            setData(res);
        } catch (e) {
            toast.error('Errore nel confronto: ' + (e.message || ''));
        } finally {
            setLoading(false);
        }
    }

    return (
        <DashboardLayout>
            <div className="max-w-6xl mx-auto space-y-6 p-4" data-testid="confronto-page">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="back-btn">
                            <ArrowLeft className="w-5 h-5" />
                        </Button>
                        <div>
                            <h1 className="text-2xl font-bold text-zinc-100">Report di Confronto</h1>
                            <p className="text-sm text-zinc-500">Preventivo AI vs Preventivo Manuale</p>
                        </div>
                    </div>
                    <Badge variant="outline" className="border-blue-600 text-blue-400 gap-1">
                        <Target className="w-3.5 h-3.5" /> Blind Test
                    </Badge>
                </div>

                {/* Selector */}
                <Card className="bg-zinc-900 border-zinc-800">
                    <CardContent className="pt-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                            <div>
                                <label className="text-xs text-zinc-500 mb-1 block">Preventivo AI</label>
                                <Select value={aiId} onValueChange={setAiId}>
                                    <SelectTrigger className="bg-zinc-800 border-zinc-700" data-testid="select-ai">
                                        <SelectValue placeholder="Seleziona preventivo AI..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {prevList.filter(p => p.predittivo).map(p => (
                                            <SelectItem key={p.preventivo_id} value={p.preventivo_id}>
                                                {p.number} - {p.subject?.substring(0, 40)}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <label className="text-xs text-zinc-500 mb-1 block">Preventivo Manuale</label>
                                <Select value={manId} onValueChange={setManId}>
                                    <SelectTrigger className="bg-zinc-800 border-zinc-700" data-testid="select-manual">
                                        <SelectValue placeholder="Seleziona preventivo Manuale..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {prevList.filter(p => !p.predittivo).map(p => (
                                            <SelectItem key={p.preventivo_id} value={p.preventivo_id}>
                                                {p.number} - {p.subject?.substring(0, 40)}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <Button onClick={runConfronto} disabled={loading || !aiId || !manId}
                                className="bg-blue-600 hover:bg-blue-700" data-testid="run-confronto-btn">
                                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <BarChart3 className="w-4 h-4 mr-2" />}
                                Confronta
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {data && (
                    <>
                        {/* Header */}
                        <div className="text-center">
                            <h2 className="text-lg font-semibold text-zinc-200">{data.titolo}</h2>
                            <p className="text-sm text-zinc-500">{data.progetto}</p>
                        </div>

                        {/* Top KPIs */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <Card className="bg-zinc-900 border-zinc-800">
                                <CardContent className="pt-4 flex flex-col items-center">
                                    <ConfidenceGauge score={data.confidence_score} giudizio={data.giudizio} />
                                    <span className="text-xs text-zinc-500 mt-1">Confidence Score</span>
                                </CardContent>
                            </Card>
                            <Card className="bg-zinc-900 border-zinc-800">
                                <CardContent className="pt-4 text-center space-y-1">
                                    <Scale className="w-6 h-6 mx-auto text-zinc-500" />
                                    <div className="text-2xl font-bold text-zinc-100">{fmtNum(data.confronto_peso?.ai, 0)} kg</div>
                                    <div className="text-xs text-zinc-500">vs {fmtNum(data.confronto_peso?.manuale, 0)} kg manuale</div>
                                    <DeltaBadge pct={data.confronto_peso?.delta_pct} />
                                </CardContent>
                            </Card>
                            <Card className="bg-zinc-900 border-zinc-800">
                                <CardContent className="pt-4 text-center space-y-1">
                                    <Clock className="w-6 h-6 mx-auto text-zinc-500" />
                                    <div className="text-2xl font-bold text-zinc-100">{fmtNum(data.confronto_ore?.ai, 0)}h</div>
                                    <div className="text-xs text-zinc-500">vs {fmtNum(data.confronto_ore?.manuale, 0)}h manuale</div>
                                    <DeltaBadge pct={data.confronto_ore?.delta_pct} />
                                </CardContent>
                            </Card>
                            <Card className="bg-zinc-900 border-zinc-800">
                                <CardContent className="pt-4 text-center space-y-1">
                                    <TrendingUp className="w-6 h-6 mx-auto text-zinc-500" />
                                    <div className="text-2xl font-bold text-zinc-100">{fmtEur(data.confronto_categorie?.subtotale?.ai)}</div>
                                    <div className="text-xs text-zinc-500">vs {fmtEur(data.confronto_categorie?.subtotale?.manuale)}</div>
                                    <DeltaBadge pct={data.scostamento_totale_pct} />
                                </CardContent>
                            </Card>
                        </div>

                        {/* Category Breakdown */}
                        <Card className="bg-zinc-900 border-zinc-800">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base text-zinc-300">Confronto per Categoria</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-5 gap-2 pb-2 border-b border-zinc-700 text-xs text-zinc-500">
                                    <div>Categoria</div>
                                    <div className="text-right">AI</div>
                                    <div className="text-right">Manuale</div>
                                    <div className="text-right">Delta</div>
                                    <div className="text-right">%</div>
                                </div>
                                <CategoryRow label="Materiali" data={data.confronto_categorie?.materiali} />
                                <CategoryRow label="Manodopera" icon={Clock} data={data.confronto_categorie?.manodopera} />
                                <CategoryRow label="Conto Lavoro" data={data.confronto_categorie?.conto_lavoro} />
                                <div className="grid grid-cols-5 gap-2 items-center py-2 bg-zinc-800/50 rounded -mx-2 px-2 mt-1">
                                    <div className="font-semibold text-sm text-zinc-200">Subtotale</div>
                                    <div className="text-right text-sm font-mono font-semibold text-blue-300">{fmtEur(data.confronto_categorie?.subtotale?.ai)}</div>
                                    <div className="text-right text-sm font-mono font-semibold text-amber-300">{fmtEur(data.confronto_categorie?.subtotale?.manuale)}</div>
                                    <div className="text-right text-sm font-mono font-semibold text-red-400">
                                        {data.confronto_categorie?.subtotale?.delta > 0 ? '+' : ''}{fmtEur(data.confronto_categorie?.subtotale?.delta)}
                                    </div>
                                    <div className="text-right"><DeltaBadge pct={data.scostamento_totale_pct} /></div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Line-by-line comparison */}
                        <Card className="bg-zinc-900 border-zinc-800">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base text-zinc-300">Confronto Riga per Riga</CardTitle>
                            </CardHeader>
                            <CardContent className="overflow-x-auto">
                                <table className="w-full text-sm" data-testid="confronto-righe-table">
                                    <thead>
                                        <tr className="text-xs text-zinc-500 border-b border-zinc-700">
                                            <th className="text-left py-2 pr-2">Voce AI</th>
                                            <th className="text-left py-2 pr-2">Voce Manuale</th>
                                            <th className="text-right py-2 px-2">AI</th>
                                            <th className="text-right py-2 px-2">Manuale</th>
                                            <th className="text-right py-2 px-2">Delta</th>
                                            <th className="text-right py-2">%</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {(data.confronto_righe || []).map((r, i) => (
                                            <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                                                <td className="py-1.5 pr-2 text-zinc-300 max-w-[200px] truncate">{r.voce_ai}</td>
                                                <td className="py-1.5 pr-2 text-zinc-400 max-w-[200px] truncate">{r.voce_manuale}</td>
                                                <td className="py-1.5 px-2 text-right font-mono text-blue-300">{fmtEur(r.importo_ai)}</td>
                                                <td className="py-1.5 px-2 text-right font-mono text-amber-300">{fmtEur(r.importo_manuale)}</td>
                                                <td className="py-1.5 px-2 text-right font-mono">
                                                    <span className={r.delta > 0 ? 'text-red-400' : r.delta < 0 ? 'text-emerald-400' : 'text-zinc-500'}>
                                                        {r.delta > 0 ? '+' : ''}{fmtEur(r.delta)}
                                                    </span>
                                                </td>
                                                <td className="py-1.5 text-right"><DeltaBadge pct={r.delta_pct} /></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </CardContent>
                        </Card>

                        {/* AI Insights */}
                        {data.insights?.length > 0 && (
                            <Card className="bg-zinc-900 border-zinc-800">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base text-zinc-300 flex items-center gap-2">
                                        <Target className="w-4 h-4 text-blue-400" /> Osservazioni AI
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <ul className="space-y-2" data-testid="insights-list">
                                        {data.insights.map((ins, i) => (
                                            <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                                                <span className="text-blue-400 mt-0.5">&#8226;</span>
                                                {ins}
                                            </li>
                                        ))}
                                    </ul>
                                </CardContent>
                            </Card>
                        )}
                    </>
                )}
            </div>
        </DashboardLayout>
    );
}
