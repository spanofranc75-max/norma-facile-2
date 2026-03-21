/**
 * TracciabilitaPage — EN 1090 FPC Material Traceability & Welders
 * Tabs: Lotti Materiale | Saldatori | Progetti FPC
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Package, Users, FolderOpen, Plus, Trash2, Edit, AlertTriangle, Download, Search, Shield } from 'lucide-react';
import { useConfirm } from '../components/ConfirmProvider';

const API = process.env.REACT_APP_BACKEND_URL;

const fetchOpts = (method, body) => {
  const opts = { method: method || 'GET', credentials: 'include', headers: {} };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  return opts;
};

// ═══════════════════════════════════════════════════════
// MATERIAL BATCHES TAB
// ═══════════════════════════════════════════════════════
function BatchesTab() {
  const [batches, setBatches] = useState([]);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ supplier_name: '', material_type: '', heat_number: '', notes: '', received_date: '' });
  const [certFile, setCertFile] = useState(null);

  const load = useCallback(async () => {
    const r = await fetch(`${API}/api/fpc/batches`, fetchOpts());
    if (r.ok) {
      const data = await r.json();
      setBatches(Array.isArray(data) ? data : data.batches || []);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => { setEditing(null); setForm({ supplier_name: '', material_type: '', heat_number: '', notes: '', received_date: '' }); setCertFile(null); setShowForm(true); };
  const openEdit = (b) => { setEditing(b.batch_id); setForm({ supplier_name: b.supplier_name, material_type: b.material_type, heat_number: b.heat_number, notes: b.notes || '', received_date: b.received_date || '' }); setCertFile(null); setShowForm(true); };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setCertFile({ base64: reader.result, filename: file.name });
    };
    reader.readAsDataURL(file);
  };

  const save = async () => {
    const payload = { ...form };
    if (certFile) {
      payload.certificate_base64 = certFile.base64;
      payload.certificate_filename = certFile.filename;
    }
    const url = editing ? `${API}/api/fpc/batches/${editing}` : `${API}/api/fpc/batches`;
    const method = editing ? 'PUT' : 'POST';
    const r = await fetch(url, fetchOpts(method, payload));
    if (r.ok) { toast.success(editing ? 'Lotto aggiornato' : 'Lotto creato'); setShowForm(false); load(); }
    else { const d = await r.json().catch(() => ({})); toast.error(d.detail || 'Errore'); }
  };

  const deleteBatch = async (id) => {
    if (!(await confirm('Eliminare questo lotto?'))) return;
    const r = await fetch(`${API}/api/fpc/batches/${id}`, fetchOpts('DELETE'));
    if (r.ok) { toast.success('Lotto eliminato'); load(); }
  };

  const downloadCert = async (id, filename) => {
    const r = await fetch(`${API}/api/fpc/batches/${id}/certificate`, fetchOpts());
    if (!r.ok) { toast.error('Certificato non disponibile'); return; }
    const data = await r.json();
    const link = document.createElement('a');
    link.href = data.certificate_base64;
    link.download = data.certificate_filename || 'certificato_3_1.pdf';
    link.click();
  };

  const filtered = batches.filter(b =>
    (b.heat_number || '').toLowerCase().includes(search.toLowerCase()) ||
    (b.supplier_name || '').toLowerCase().includes(search.toLowerCase()) ||
    (b.material_type || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="relative w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input data-testid="batch-search" placeholder="Cerca per colata, fornitore, materiale..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9" />
        </div>
        <Button data-testid="new-batch-btn" onClick={openNew} className="bg-[#0055FF] hover:bg-[#0044CC]"><Plus className="h-4 w-4 mr-1" /> Nuovo Lotto</Button>
      </div>

      <div className="overflow-x-auto bg-white rounded-lg border">
        <table className="w-full text-sm" data-testid="batches-table">
          <thead><tr className="border-b text-slate-500 text-xs uppercase bg-slate-50">
            <th className="text-left py-2 px-3">N. Colata</th>
            <th className="text-left py-2 px-3">Materiale</th>
            <th className="text-left py-2 px-3">Fornitore</th>
            <th className="text-left py-2 px-3">Data Ric.</th>
            <th className="text-center py-2 px-3">Cert. 3.1</th>
            <th className="text-right py-2 px-3">Azioni</th>
          </tr></thead>
          <tbody>
            {filtered.map(b => (
              <tr key={b.batch_id} className="border-b hover:bg-slate-50">
                <td className="py-2 px-3 font-mono font-bold text-[#0055FF]">{b.heat_number}</td>
                <td className="py-2 px-3">{b.material_type}</td>
                <td className="py-2 px-3">{b.supplier_name}</td>
                <td className="py-2 px-3 text-slate-400">{b.received_date || '-'}</td>
                <td className="py-2 px-3 text-center">
                  {b.has_certificate ? (
                    <button data-testid={`download-cert-${b.batch_id}`} onClick={() => downloadCert(b.batch_id, b.certificate_filename)} className="text-emerald-500 hover:text-emerald-600"><Download className="h-4 w-4 inline" /></button>
                  ) : <span className="text-slate-300">-</span>}
                </td>
                <td className="py-2 px-3 text-right space-x-1">
                  <button data-testid={`edit-batch-${b.batch_id}`} onClick={() => openEdit(b)} className="text-slate-400 hover:text-slate-700"><Edit className="h-4 w-4 inline" /></button>
                  <button data-testid={`delete-batch-${b.batch_id}`} onClick={() => deleteBatch(b.batch_id)} className="text-red-400 hover:text-red-500"><Trash2 className="h-4 w-4 inline" /></button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-slate-400">Nessun lotto registrato</td></tr>}
          </tbody>
        </table>
      </div>

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editing ? 'Modifica Lotto' : 'Nuovo Lotto Materiale'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><label className="text-xs text-slate-500">Fornitore *</label><Input data-testid="batch-supplier" value={form.supplier_name} onChange={e => setForm({ ...form, supplier_name: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs text-slate-500">Tipo Materiale *</label><Input data-testid="batch-material" placeholder="es. S275JR" value={form.material_type} onChange={e => setForm({ ...form, material_type: e.target.value })} /></div>
              <div><label className="text-xs text-slate-500">N. Colata (Heat Number) *</label><Input data-testid="batch-heat" value={form.heat_number} onChange={e => setForm({ ...form, heat_number: e.target.value })} /></div>
            </div>
            <div><label className="text-xs text-slate-500">Data Ricevimento</label><Input data-testid="batch-date" type="date" value={form.received_date} onChange={e => setForm({ ...form, received_date: e.target.value })} /></div>
            <div><label className="text-xs text-slate-500">Certificato 3.1 (PDF)</label><input data-testid="batch-cert-upload" type="file" accept=".pdf" onChange={handleFileChange} className="w-full text-sm file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:bg-slate-100 file:text-slate-700" /></div>
            <div><label className="text-xs text-slate-500">Note</label><Input data-testid="batch-notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button data-testid="save-batch-btn" onClick={save} className="bg-[#0055FF] hover:bg-[#0044CC]" disabled={!form.supplier_name || !form.material_type || !form.heat_number}>Salva</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// WELDERS TAB
// ═══════════════════════════════════════════════════════
function WeldersTab() {
  const [welders, setWelders] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', qualification_level: '', license_expiry: '', notes: '' });

  const load = useCallback(async () => {
    const r = await fetch(`${API}/api/fpc/welders`, fetchOpts());
    if (r.ok) { const d = await r.json(); setWelders(Array.isArray(d) ? d : d.welders || []); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => { setEditing(null); setForm({ name: '', qualification_level: '', license_expiry: '', notes: '' }); setShowForm(true); };
  const openEdit = (w) => { setEditing(w.welder_id); setForm({ name: w.name, qualification_level: w.qualification_level || '', license_expiry: w.license_expiry || '', notes: w.notes || '' }); setShowForm(true); };

  const save = async () => {
    const url = editing ? `${API}/api/fpc/welders/${editing}` : `${API}/api/fpc/welders`;
    const method = editing ? 'PUT' : 'POST';
    const r = await fetch(url, fetchOpts(method, form));
    if (r.ok) { toast.success(editing ? 'Saldatore aggiornato' : 'Saldatore registrato'); setShowForm(false); load(); }
    else { const d = await r.json().catch(() => ({})); toast.error(d.detail || 'Errore'); }
  };

  const deleteWelder = async (id) => {
    if (!(await confirm('Eliminare questo saldatore?'))) return;
    const r = await fetch(`${API}/api/fpc/welders/${id}`, fetchOpts('DELETE'));
    if (r.ok) { toast.success('Saldatore eliminato'); load(); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-500">Registro saldatori con qualifiche ISO 9606-1</p>
        <Button data-testid="new-welder-btn" onClick={openNew} className="bg-[#0055FF] hover:bg-[#0044CC]"><Plus className="h-4 w-4 mr-1" /> Nuovo Saldatore</Button>
      </div>

      <div className="space-y-2" data-testid="welders-list">
        {welders.map(w => (
          <div key={w.welder_id} className={`flex items-center justify-between p-3 rounded-lg border ${w.is_expired ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-white'}`}>
            <div>
              <div className="font-medium flex items-center gap-2">
                {w.name}
                {w.is_expired && <span className="flex items-center text-xs text-red-500"><AlertTriangle className="h-3 w-3 mr-1" /> Qualifica scaduta</span>}
              </div>
              <div className="text-xs text-slate-400">{w.qualification_level || 'Qualifica non specificata'}</div>
              {w.license_expiry && <div className="text-xs text-slate-400">Scadenza: {w.license_expiry}</div>}
            </div>
            <div className="flex gap-2">
              <button data-testid={`edit-welder-${w.welder_id}`} onClick={() => openEdit(w)} className="text-slate-400 hover:text-slate-700"><Edit className="h-4 w-4" /></button>
              <button data-testid={`delete-welder-${w.welder_id}`} onClick={() => deleteWelder(w.welder_id)} className="text-red-400 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
            </div>
          </div>
        ))}
        {welders.length === 0 && <p className="text-center py-8 text-slate-400">Nessun saldatore registrato</p>}
      </div>

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{editing ? 'Modifica Saldatore' : 'Nuovo Saldatore'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><label className="text-xs text-slate-500">Nome *</label><Input data-testid="welder-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
            <div><label className="text-xs text-slate-500">Livello Qualifica (ISO 9606-1)</label><Input data-testid="welder-qual" placeholder="es. ISO 9606-1 135 P BW" value={form.qualification_level} onChange={e => setForm({ ...form, qualification_level: e.target.value })} /></div>
            <div><label className="text-xs text-slate-500">Scadenza Qualifica</label><Input data-testid="welder-expiry" type="date" value={form.license_expiry} onChange={e => setForm({ ...form, license_expiry: e.target.value })} /></div>
            <div><label className="text-xs text-slate-500">Note</label><Input data-testid="welder-notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button data-testid="save-welder-btn" onClick={save} className="bg-[#0055FF] hover:bg-[#0044CC]" disabled={!form.name}>Salva</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// FPC PROJECTS TAB
// ═══════════════════════════════════════════════════════
function ProjectsTab() {
  const [projects, setProjects] = useState([]);
  const [preventivi, setPreventivi] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedPrev, setSelectedPrev] = useState('');
  const [execClass, setExecClass] = useState('EXC2');
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    const r = await fetch(`${API}/api/fpc/projects`, fetchOpts());
    if (r.ok) { const d = await r.json(); setProjects(Array.isArray(d) ? d : d.projects || []); }
  }, []);

  const loadPreventivi = useCallback(async () => {
    const r = await fetch(`${API}/api/preventivi/`, fetchOpts());
    if (r.ok) {
      const d = await r.json();
      const items = d.preventivi || d.items || (Array.isArray(d) ? d : []);
      const valid = items.filter(p => p.status !== 'eliminato');
      setPreventivi(valid);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    loadPreventivi();
    setSelectedPrev('');
    setExecClass('EXC2');
    setShowCreate(true);
  };

  const createProject = async () => {
    if (!selectedPrev) { toast.error('Seleziona un preventivo'); return; }
    setCreating(true);
    try {
      const r = await fetch(`${API}/api/fpc/projects`, fetchOpts('POST', {
        preventivo_id: selectedPrev,
        execution_class: execClass,
      }));
      if (r.ok) {
        const data = await r.json();
        toast.success('Progetto FPC creato!');
        setShowCreate(false);
        load();
        navigate(`/tracciabilita/progetto/${data.project_id}`);
      } else {
        const d = await r.json().catch(() => ({}));
        toast.error(d.detail || 'Errore nella creazione');
      }
    } catch (e) { toast.error('Errore: ' + e.message); }
    finally { setCreating(false); }
  };

  const getStatusBadge = (p) => {
    const fpc = p.fpc_data || {};
    if (fpc.ce_label_generated) return <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-700 border border-green-200">CE Generato</span>;
    if (p.status === 'completed') return <span className="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700 border border-blue-200">Completato</span>;
    return <span className="px-2 py-0.5 rounded text-xs bg-amber-100 text-amber-700 border border-amber-200">In Corso</span>;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-500">Progetti creati da preventivi con tracciabilita FPC</p>
        <Button data-testid="new-project-btn" onClick={openCreate} className="bg-[#0055FF] hover:bg-[#0044CC]">
          <Plus className="h-4 w-4 mr-1" /> Crea Progetto FPC
        </Button>
      </div>

      <div className="space-y-2" data-testid="projects-list">
        {projects.map(p => (
          <div key={p.project_id} data-testid={`project-row-${p.project_id}`} className="flex items-center justify-between p-3 rounded-lg border border-slate-200 bg-white cursor-pointer hover:border-[#0055FF]/50 hover:shadow-sm transition-all" onClick={() => navigate(`/tracciabilita/progetto/${p.project_id}`)}>
            <div>
              <div className="font-medium flex items-center gap-2">
                {p.preventivo_number || p.project_id}
                {getStatusBadge(p)}
              </div>
              <div className="text-sm text-slate-500">{p.client_name || 'N/A'} — {p.subject || 'Senza oggetto'}</div>
              <div className="text-xs text-slate-400">Classe: {p.fpc_data?.execution_class || '-'}</div>
            </div>
            <Shield className="h-5 w-5 text-slate-300" />
          </div>
        ))}
        {projects.length === 0 && <p className="text-center py-8 text-slate-400">Nessun progetto FPC. Clicca "Crea Progetto FPC" per iniziare.</p>}
      </div>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Crea Progetto FPC da Preventivo</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-500 font-medium">Preventivo *</label>
              <select data-testid="select-preventivo" value={selectedPrev} onChange={e => setSelectedPrev(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm mt-1 bg-white">
                <option value="">-- Seleziona preventivo --</option>
                {preventivi.map(p => (
                  <option key={p.preventivo_id} value={p.preventivo_id}>
                    {p.number} — {p.client_name || 'N/A'} — {p.subject || 'Senza oggetto'}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 font-medium">Classe di Esecuzione (EN 1090) *</label>
              <select data-testid="select-exec-class" value={execClass} onChange={e => setExecClass(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm mt-1 bg-white">
                <option value="EXC1">EXC1 — Base</option>
                <option value="EXC2">EXC2 — Standard (piu comune)</option>
                <option value="EXC3">EXC3 — Alta</option>
                <option value="EXC4">EXC4 — Massima</option>
              </select>
            </div>
            {selectedPrev && (
              <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-700">
                Il preventivo selezionato verra convertito in un progetto FPC con tracciabilita materiali, controlli qualita e generazione etichetta CE.
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Annulla</Button>
            <Button data-testid="confirm-create-project" onClick={createProject} className="bg-[#0055FF] hover:bg-[#0044CC]"
              disabled={!selectedPrev || creating}>
              {creating ? 'Creazione...' : 'Crea Progetto'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════
export default function TracciabilitaPage() {
    const confirm = useConfirm();
  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-1" data-testid="tracciabilita-title">Tracciabilit&agrave; EN 1090</h1>
        <p className="text-slate-500 mb-6">Factory Production Control — Gestione materiali, saldatori e progetti</p>

        <Tabs defaultValue="batches" className="w-full">
          <TabsList className="bg-white border mb-4">
            <TabsTrigger data-testid="tab-batches" value="batches"><Package className="h-4 w-4 mr-1" /> Lotti Materiale</TabsTrigger>
            <TabsTrigger data-testid="tab-welders" value="welders"><Users className="h-4 w-4 mr-1" /> Saldatori</TabsTrigger>
            <TabsTrigger data-testid="tab-projects" value="projects"><FolderOpen className="h-4 w-4 mr-1" /> Progetti FPC</TabsTrigger>
          </TabsList>
          <TabsContent value="batches"><BatchesTab /></TabsContent>
          <TabsContent value="welders"><WeldersTab /></TabsContent>
          <TabsContent value="projects"><ProjectsTab /></TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
