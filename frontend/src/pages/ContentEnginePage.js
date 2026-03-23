/**
 * ContentEnginePage — Main content engine with tabs for Sources, Ideas, Drafts, Queue.
 */
import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../lib/utils';
import DashboardLayout from '../components/DashboardLayout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import {
    Sparkles, FileText, Send, Lightbulb, Loader2,
    Plus, Trash2, ChevronRight, CheckCircle2, XCircle,
    Clock, Eye, Pencil, BookOpen, Video, LayoutGrid, Target,
} from 'lucide-react';

const FORMAT_LABELS = {
    linkedin_post: { label: 'LinkedIn', icon: FileText, color: 'text-blue-600 bg-blue-50' },
    reel_short: { label: 'Reel/Short', icon: Video, color: 'text-pink-600 bg-pink-50' },
    carosello: { label: 'Carosello', icon: LayoutGrid, color: 'text-violet-600 bg-violet-50' },
    case_study: { label: 'Case Study', icon: BookOpen, color: 'text-emerald-600 bg-emerald-50' },
};

const STATUS_LABELS = {
    in_review: { label: 'In revisione', color: 'bg-amber-100 text-amber-700' },
    approved: { label: 'Approvato', color: 'bg-emerald-100 text-emerald-700' },
    scheduled: { label: 'Programmato', color: 'bg-blue-100 text-blue-700' },
    published: { label: 'Pubblicato', color: 'bg-green-100 text-green-800' },
    rejected: { label: 'Scartato', color: 'bg-red-100 text-red-700' },
};

export default function ContentEnginePage() {
    const [tab, setTab] = useState('sources');
    const [stats, setStats] = useState(null);
    const [sources, setSources] = useState([]);
    const [ideas, setIdeas] = useState([]);
    const [drafts, setDrafts] = useState([]);
    const [queue, setQueue] = useState([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(null);
    const [selectedDraft, setSelectedDraft] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [st, sr, id, dr, qu] = await Promise.all([
                apiRequest('/content/stats'),
                apiRequest('/content/sources'),
                apiRequest('/content/ideas'),
                apiRequest('/content/drafts'),
                apiRequest('/content/queue'),
            ]);
            setStats(st); setSources(sr); setIdeas(id); setDrafts(dr); setQueue(qu);
        } catch {} finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const seedSources = async () => {
        setGenerating('seed');
        try {
            await apiRequest('/content/seed-sources', { method: 'POST' });
            await load();
        } catch {} finally { setGenerating(null); }
    };

    const generateIdeas = async (sourceId) => {
        setGenerating(sourceId);
        try {
            await apiRequest(`/content/sources/${sourceId}/generate-ideas`, { method: 'POST' });
            await load();
            setTab('ideas');
        } catch {} finally { setGenerating(null); }
    };

    const generateDraft = async (ideaId) => {
        setGenerating(ideaId);
        try {
            await apiRequest(`/content/ideas/${ideaId}/generate-draft`, { method: 'POST' });
            await load();
            setTab('drafts');
        } catch {} finally { setGenerating(null); }
    };

    const addToQueue = async (draftId) => {
        try {
            await apiRequest('/content/queue', { method: 'POST', body: JSON.stringify({ draft_id: draftId }) });
            await load();
            setTab('queue');
        } catch {}
    };

    const updateQueueStatus = async (queueId, status) => {
        try {
            await apiRequest(`/content/queue/${queueId}`, { method: 'PUT', body: JSON.stringify({ status }) });
            await load();
        } catch {}
    };

    const deleteItem = async (type, id) => {
        try {
            await apiRequest(`/content/${type}/${id}`, { method: 'DELETE' });
            await load();
        } catch {}
    };

    if (loading) return (
        <DashboardLayout>
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-[#0055FF]" />
            </div>
        </DashboardLayout>
    );

    return (
        <DashboardLayout>
            <div className="p-4 lg:p-6 max-w-7xl mx-auto" data-testid="content-engine">
                {/* Header */}
                <div className="flex items-center justify-between mb-5">
                    <div>
                        <h1 className="text-lg font-bold text-slate-800">Contenuti</h1>
                        <p className="text-xs text-slate-500 mt-0.5">Produci contenuti marketing dal valore reale del prodotto</p>
                    </div>
                    {stats && (
                        <div className="flex gap-3 text-xs">
                            <span className="px-2.5 py-1 bg-slate-100 rounded-lg font-medium">{stats.sources} sorgenti</span>
                            <span className="px-2.5 py-1 bg-blue-50 text-blue-700 rounded-lg font-medium">{stats.ideas} idee</span>
                            <span className="px-2.5 py-1 bg-violet-50 text-violet-700 rounded-lg font-medium">{stats.drafts} bozze</span>
                            <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg font-medium">{stats.queue_approved} approvate</span>
                        </div>
                    )}
                </div>

                <Tabs value={tab} onValueChange={setTab}>
                    <TabsList className="mb-4">
                        <TabsTrigger value="sources" data-testid="tab-sources">
                            <Target className="h-3.5 w-3.5 mr-1.5" />Sorgenti
                        </TabsTrigger>
                        <TabsTrigger value="ideas" data-testid="tab-ideas">
                            <Lightbulb className="h-3.5 w-3.5 mr-1.5" />Idee
                        </TabsTrigger>
                        <TabsTrigger value="drafts" data-testid="tab-drafts">
                            <Pencil className="h-3.5 w-3.5 mr-1.5" />Bozze
                        </TabsTrigger>
                        <TabsTrigger value="queue" data-testid="tab-queue">
                            <Send className="h-3.5 w-3.5 mr-1.5" />Coda
                        </TabsTrigger>
                    </TabsList>

                    {/* SOURCES TAB */}
                    <TabsContent value="sources">
                        {sources.length === 0 ? (
                            <Card className="border-dashed border-2">
                                <CardContent className="flex flex-col items-center py-10">
                                    <Target className="h-10 w-10 text-slate-300 mb-3" />
                                    <p className="text-sm font-semibold text-slate-700">Nessuna sorgente contenuto</p>
                                    <p className="text-xs text-slate-500 mt-1">Carica le sorgenti pre-configurate per iniziare</p>
                                    <Button onClick={seedSources} className="mt-4 bg-[#0055FF] text-white text-xs" disabled={generating === 'seed'} data-testid="btn-seed-sources">
                                        {generating === 'seed' ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Plus className="h-3.5 w-3.5 mr-1.5" />}
                                        Carica 10 sorgenti
                                    </Button>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid gap-3">
                                {sources.map(src => (
                                    <Card key={src.source_id} className="hover:border-blue-200 transition-colors" data-testid={`source-${src.source_id}`}>
                                        <CardContent className="p-4 flex items-start gap-3">
                                            <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center shrink-0 mt-0.5">
                                                <Target className="h-4 w-4 text-blue-600" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <h3 className="text-sm font-bold text-slate-800">{src.title}</h3>
                                                    <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">{src.type}</span>
                                                </div>
                                                <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{src.description}</p>
                                                {src.pain_points?.length > 0 && (
                                                    <div className="flex flex-wrap gap-1 mt-1.5">
                                                        {src.pain_points.slice(0, 3).map((p, i) => (
                                                            <span key={i} className="text-[10px] px-1.5 py-0.5 bg-red-50 text-red-600 rounded">{p.length > 40 ? p.slice(0, 40) + '...' : p}</span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                            <Button size="sm" className="bg-[#0055FF] text-white text-xs h-8 shrink-0" onClick={() => generateIdeas(src.source_id)} disabled={!!generating} data-testid={`btn-generate-ideas-${src.source_id}`}>
                                                {generating === src.source_id ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Sparkles className="h-3 w-3 mr-1" />}
                                                Genera Idee
                                            </Button>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </TabsContent>

                    {/* IDEAS TAB */}
                    <TabsContent value="ideas">
                        {ideas.length === 0 ? (
                            <Card className="border-dashed border-2">
                                <CardContent className="flex flex-col items-center py-10">
                                    <Lightbulb className="h-10 w-10 text-slate-300 mb-3" />
                                    <p className="text-sm font-semibold text-slate-700">Nessuna idea ancora</p>
                                    <p className="text-xs text-slate-500 mt-1">Vai alle Sorgenti e genera idee con l'AI</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {ideas.map(idea => {
                                    const fmt = FORMAT_LABELS[idea.format] || FORMAT_LABELS.linkedin_post;
                                    const FmtIcon = fmt.icon;
                                    return (
                                        <Card key={idea.idea_id} className="hover:shadow-md transition-shadow" data-testid={`idea-${idea.idea_id}`}>
                                            <CardContent className="p-4">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1 ${fmt.color}`}>
                                                        <FmtIcon className="h-3 w-3" />{fmt.label}
                                                    </span>
                                                    <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">{idea.angle}</span>
                                                </div>
                                                <p className="text-sm font-semibold text-slate-800 leading-snug">{idea.hook}</p>
                                                <p className="text-xs text-slate-500 mt-1.5">{idea.brief}</p>
                                                <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100">
                                                    <span className="text-[10px] text-slate-400">{idea.target_audience}</span>
                                                    <div className="flex gap-1.5">
                                                        <Button size="sm" variant="ghost" className="h-7 text-xs text-red-500" onClick={() => deleteItem('ideas', idea.idea_id)}>
                                                            <Trash2 className="h-3 w-3" />
                                                        </Button>
                                                        <Button size="sm" className="h-7 text-xs bg-[#0055FF] text-white" onClick={() => generateDraft(idea.idea_id)} disabled={!!generating || idea.status === 'draft_generated'} data-testid={`btn-draft-${idea.idea_id}`}>
                                                            {generating === idea.idea_id ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Pencil className="h-3 w-3 mr-1" />}
                                                            {idea.status === 'draft_generated' ? 'Bozza creata' : 'Crea Bozza'}
                                                        </Button>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </div>
                        )}
                    </TabsContent>

                    {/* DRAFTS TAB */}
                    <TabsContent value="drafts">
                        {selectedDraft ? (
                            <DraftDetail draft={selectedDraft} onBack={() => setSelectedDraft(null)} onQueue={addToQueue} />
                        ) : drafts.length === 0 ? (
                            <Card className="border-dashed border-2">
                                <CardContent className="flex flex-col items-center py-10">
                                    <Pencil className="h-10 w-10 text-slate-300 mb-3" />
                                    <p className="text-sm font-semibold text-slate-700">Nessuna bozza</p>
                                    <p className="text-xs text-slate-500 mt-1">Genera bozze dalle idee nella tab Idee</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid gap-3">
                                {drafts.map(d => {
                                    const fmt = FORMAT_LABELS[d.format] || FORMAT_LABELS.linkedin_post;
                                    const FmtIcon = fmt.icon;
                                    return (
                                        <Card key={d.draft_id} className="hover:border-blue-200 transition-colors cursor-pointer" onClick={() => setSelectedDraft(d)} data-testid={`draft-${d.draft_id}`}>
                                            <CardContent className="p-4 flex items-start gap-3">
                                                <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${fmt.color}`}>
                                                    <FmtIcon className="h-4 w-4" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2">
                                                        <h3 className="text-sm font-bold text-slate-800 line-clamp-1">{d.title}</h3>
                                                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${fmt.color}`}>{fmt.label}</span>
                                                    </div>
                                                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{d.body?.slice(0, 120)}...</p>
                                                    {d.hashtags?.length > 0 && (
                                                        <p className="text-[10px] text-blue-500 mt-1">{d.hashtags.slice(0, 4).join(' ')}</p>
                                                    )}
                                                </div>
                                                <div className="flex gap-1.5 shrink-0">
                                                    {d.status !== 'queued' && (
                                                        <Button size="sm" className="h-7 text-xs bg-emerald-600 text-white" onClick={(e) => { e.stopPropagation(); addToQueue(d.draft_id); }} data-testid={`btn-queue-${d.draft_id}`}>
                                                            <Send className="h-3 w-3 mr-1" />Coda
                                                        </Button>
                                                    )}
                                                    <ChevronRight className="h-4 w-4 text-slate-400 mt-1.5" />
                                                </div>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </div>
                        )}
                    </TabsContent>

                    {/* QUEUE TAB */}
                    <TabsContent value="queue">
                        {queue.length === 0 ? (
                            <Card className="border-dashed border-2">
                                <CardContent className="flex flex-col items-center py-10">
                                    <Send className="h-10 w-10 text-slate-300 mb-3" />
                                    <p className="text-sm font-semibold text-slate-700">Coda editoriale vuota</p>
                                    <p className="text-xs text-slate-500 mt-1">Aggiungi bozze alla coda per organizzare la pubblicazione</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="space-y-2">
                                {queue.map(q => {
                                    const st = STATUS_LABELS[q.status] || STATUS_LABELS.in_review;
                                    return (
                                        <Card key={q.queue_id} data-testid={`queue-${q.queue_id}`}>
                                            <CardContent className="p-3 flex items-center gap-3">
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2">
                                                        <h3 className="text-sm font-semibold text-slate-800 line-clamp-1">{q.draft_title || 'Bozza'}</h3>
                                                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${st.color}`}>{st.label}</span>
                                                    </div>
                                                    <p className="text-[11px] text-slate-500 mt-0.5">{q.channel} {q.draft_format ? `· ${FORMAT_LABELS[q.draft_format]?.label || q.draft_format}` : ''}</p>
                                                </div>
                                                <div className="flex gap-1.5 shrink-0">
                                                    {q.status === 'in_review' && (
                                                        <>
                                                            <Button size="sm" className="h-7 text-xs bg-emerald-600 text-white" onClick={() => updateQueueStatus(q.queue_id, 'approved')} data-testid={`btn-approve-${q.queue_id}`}>
                                                                <CheckCircle2 className="h-3 w-3 mr-1" />Approva
                                                            </Button>
                                                            <Button size="sm" variant="ghost" className="h-7 text-xs text-red-500" onClick={() => updateQueueStatus(q.queue_id, 'rejected')}>
                                                                <XCircle className="h-3 w-3 mr-1" />Scarta
                                                            </Button>
                                                        </>
                                                    )}
                                                    {q.status === 'approved' && (
                                                        <Button size="sm" className="h-7 text-xs bg-blue-600 text-white" onClick={() => updateQueueStatus(q.queue_id, 'published')} data-testid={`btn-publish-${q.queue_id}`}>
                                                            <CheckCircle2 className="h-3 w-3 mr-1" />Pubblicato
                                                        </Button>
                                                    )}
                                                    <Button size="sm" variant="ghost" className="h-7 text-xs text-slate-400" onClick={() => deleteItem('queue', q.queue_id)}>
                                                        <Trash2 className="h-3 w-3" />
                                                    </Button>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </div>
                        )}
                    </TabsContent>
                </Tabs>
            </div>
        </DashboardLayout>
    );
}


function DraftDetail({ draft, onBack, onQueue }) {
    const fmt = FORMAT_LABELS[draft.format] || FORMAT_LABELS.linkedin_post;
    const FmtIcon = fmt.icon;

    return (
        <div data-testid="draft-detail">
            <Button variant="ghost" className="mb-3 text-xs text-slate-500" onClick={onBack}>
                &larr; Torna alle bozze
            </Button>
            <Card>
                <CardContent className="p-5">
                    <div className="flex items-center gap-2 mb-3">
                        <span className={`text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1.5 ${fmt.color}`}>
                            <FmtIcon className="h-3.5 w-3.5" />{fmt.label}
                        </span>
                        {draft.suggested_asset_type && (
                            <span className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-500 rounded">Asset: {draft.suggested_asset_type}</span>
                        )}
                    </div>
                    <h2 className="text-base font-bold text-slate-800 mb-3">{draft.title}</h2>

                    {draft.format === 'carosello' && draft.slides?.length > 0 ? (
                        <div className="space-y-2 mb-4">
                            {draft.slides.map((slide, i) => (
                                <div key={i} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                                    <p className="text-xs font-bold text-slate-700">Slide {i + 1}: {slide.title}</p>
                                    <p className="text-xs text-slate-600 mt-0.5">{slide.body}</p>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="prose prose-sm max-w-none mb-4">
                            <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{draft.body}</div>
                        </div>
                    )}

                    {draft.cta && (
                        <div className="p-3 bg-blue-50 rounded-lg mb-3">
                            <p className="text-xs font-semibold text-blue-700">CTA: {draft.cta}</p>
                        </div>
                    )}

                    {draft.hashtags?.length > 0 && (
                        <p className="text-xs text-blue-500 mb-4">{draft.hashtags.join(' ')}</p>
                    )}

                    {draft.status !== 'queued' && (
                        <Button className="bg-emerald-600 text-white text-xs" onClick={() => onQueue(draft.draft_id)}>
                            <Send className="h-3.5 w-3.5 mr-1.5" />Aggiungi alla Coda Editoriale
                        </Button>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
