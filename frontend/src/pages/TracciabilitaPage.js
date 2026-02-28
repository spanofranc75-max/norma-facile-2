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

const API = process.env.REACT_APP_BACKEND_URL;

function getHeaders() {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

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
    const r = await fetch(`${API}/api/fpc/batches`, { headers: getHeaders() });
    if (r.ok) setBatches(await r.json());
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
    const r = await fetch(url, { method, headers: getHeaders(), body: JSON.stringify(payload) });
    if (r.ok) { toast.success(editing ? 'Lotto aggiornato' : 'Lotto creato'); setShowForm(false); load(); }
    else { const d = await r.json().catch(() => ({})); toast.error(d.detail || 'Errore'); }
  };

  const deleteBatch = async (id) => {
    if (!window.confirm('Eliminare questo lotto?')) return;
    const r = await fetch(`${API}/api/fpc/batches/${id}`, { method: 'DELETE', headers: getHeaders() });
    if (r.ok) { toast.success('Lotto eliminato'); load(); }
  };

  const downloadCert = async (id, filename) => {
    const r = await fetch(`${API}/api/fpc/batches/${id}/certificate`, { headers: getHeaders() });
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
        <DialogContent className="bg-zinc-900 border-zinc-700 text-white max-w-lg">
          <DialogHeader><DialogTitle>{editing ? 'Modifica Lotto' : 'Nuovo Lotto Materiale'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><label className="text-xs text-zinc-400">Fornitore *</label><Input data-testid="batch-supplier" value={form.supplier_name} onChange={e => setForm({ ...form, supplier_name: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs text-zinc-400">Tipo Materiale *</label><Input data-testid="batch-material" placeholder="es. S275JR" value={form.material_type} onChange={e => setForm({ ...form, material_type: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
              <div><label className="text-xs text-zinc-400">N. Colata (Heat Number) *</label><Input data-testid="batch-heat" value={form.heat_number} onChange={e => setForm({ ...form, heat_number: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
            </div>
            <div><label className="text-xs text-zinc-400">Data Ricevimento</label><Input data-testid="batch-date" type="date" value={form.received_date} onChange={e => setForm({ ...form, received_date: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
            <div><label className="text-xs text-zinc-400">Certificato 3.1 (PDF)</label><input data-testid="batch-cert-upload" type="file" accept=".pdf" onChange={handleFileChange} className="w-full text-sm text-zinc-400 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:bg-zinc-700 file:text-white" /></div>
            <div><label className="text-xs text-zinc-400">Note</label><Input data-testid="batch-notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
          </div>
          <DialogFooter>
            <Button data-testid="save-batch-btn" onClick={save} className="bg-amber-600 hover:bg-amber-500" disabled={!form.supplier_name || !form.material_type || !form.heat_number}>Salva</Button>
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
    const r = await fetch(`${API}/api/fpc/welders`, { headers: getHeaders() });
    if (r.ok) setWelders(await r.json());
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => { setEditing(null); setForm({ name: '', qualification_level: '', license_expiry: '', notes: '' }); setShowForm(true); };
  const openEdit = (w) => { setEditing(w.welder_id); setForm({ name: w.name, qualification_level: w.qualification_level || '', license_expiry: w.license_expiry || '', notes: w.notes || '' }); setShowForm(true); };

  const save = async () => {
    const url = editing ? `${API}/api/fpc/welders/${editing}` : `${API}/api/fpc/welders`;
    const method = editing ? 'PUT' : 'POST';
    const r = await fetch(url, { method, headers: getHeaders(), body: JSON.stringify(form) });
    if (r.ok) { toast.success(editing ? 'Saldatore aggiornato' : 'Saldatore registrato'); setShowForm(false); load(); }
    else { const d = await r.json().catch(() => ({})); toast.error(d.detail || 'Errore'); }
  };

  const deleteWelder = async (id) => {
    if (!window.confirm('Eliminare questo saldatore?')) return;
    const r = await fetch(`${API}/api/fpc/welders/${id}`, { method: 'DELETE', headers: getHeaders() });
    if (r.ok) { toast.success('Saldatore eliminato'); load(); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-zinc-400">Registro saldatori con qualifiche ISO 9606-1</p>
        <Button data-testid="new-welder-btn" onClick={openNew} className="bg-amber-600 hover:bg-amber-500"><Plus className="h-4 w-4 mr-1" /> Nuovo Saldatore</Button>
      </div>

      <div className="space-y-2" data-testid="welders-list">
        {welders.map(w => (
          <div key={w.welder_id} className={`flex items-center justify-between p-3 rounded-lg border ${w.is_expired ? 'border-red-500/50 bg-red-900/10' : 'border-zinc-700 bg-zinc-800/50'}`}>
            <div>
              <div className="font-medium flex items-center gap-2">
                {w.name}
                {w.is_expired && <span className="flex items-center text-xs text-red-400"><AlertTriangle className="h-3 w-3 mr-1" /> Qualifica scaduta</span>}
              </div>
              <div className="text-xs text-zinc-400">{w.qualification_level || 'Qualifica non specificata'}</div>
              {w.license_expiry && <div className="text-xs text-zinc-500">Scadenza: {w.license_expiry}</div>}
            </div>
            <div className="flex gap-2">
              <button data-testid={`edit-welder-${w.welder_id}`} onClick={() => openEdit(w)} className="text-zinc-400 hover:text-white"><Edit className="h-4 w-4" /></button>
              <button data-testid={`delete-welder-${w.welder_id}`} onClick={() => deleteWelder(w.welder_id)} className="text-red-400 hover:text-red-300"><Trash2 className="h-4 w-4" /></button>
            </div>
          </div>
        ))}
        {welders.length === 0 && <p className="text-center py-8 text-zinc-500">Nessun saldatore registrato</p>}
      </div>

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="bg-zinc-900 border-zinc-700 text-white max-w-md">
          <DialogHeader><DialogTitle>{editing ? 'Modifica Saldatore' : 'Nuovo Saldatore'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><label className="text-xs text-zinc-400">Nome *</label><Input data-testid="welder-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
            <div><label className="text-xs text-zinc-400">Livello Qualifica (ISO 9606-1)</label><Input data-testid="welder-qual" placeholder="es. ISO 9606-1 135 P BW" value={form.qualification_level} onChange={e => setForm({ ...form, qualification_level: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
            <div><label className="text-xs text-zinc-400">Scadenza Qualifica</label><Input data-testid="welder-expiry" type="date" value={form.license_expiry} onChange={e => setForm({ ...form, license_expiry: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
            <div><label className="text-xs text-zinc-400">Note</label><Input data-testid="welder-notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className="bg-zinc-800 border-zinc-700" /></div>
          </div>
          <DialogFooter>
            <Button data-testid="save-welder-btn" onClick={save} className="bg-amber-600 hover:bg-amber-500" disabled={!form.name}>Salva</Button>
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
  const navigate = useNavigate();

  const load = useCallback(async () => {
    const r = await fetch(`${API}/api/fpc/projects`, { headers: getHeaders() });
    if (r.ok) setProjects(await r.json());
  }, []);

  useEffect(() => { load(); }, [load]);

  const getStatusBadge = (p) => {
    const fpc = p.fpc_data || {};
    if (fpc.ce_label_generated) return <span className="px-2 py-0.5 rounded text-xs bg-green-600/20 text-green-400">CE Generato</span>;
    if (p.status === 'completed') return <span className="px-2 py-0.5 rounded text-xs bg-blue-600/20 text-blue-400">Completato</span>;
    return <span className="px-2 py-0.5 rounded text-xs bg-amber-600/20 text-amber-400">In Corso</span>;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-zinc-400">Progetti creati da preventivi con tracciabilità FPC</p>
      </div>

      <div className="space-y-2" data-testid="projects-list">
        {projects.map(p => (
          <div key={p.project_id} className="flex items-center justify-between p-3 rounded-lg border border-zinc-700 bg-zinc-800/50 cursor-pointer hover:border-amber-500/50" onClick={() => navigate(`/tracciabilita/progetto/${p.project_id}`)}>
            <div>
              <div className="font-medium flex items-center gap-2">
                {p.preventivo_number || p.project_id}
                {getStatusBadge(p)}
              </div>
              <div className="text-sm text-zinc-400">{p.client_name || 'N/A'} — {p.subject || 'Senza oggetto'}</div>
              <div className="text-xs text-zinc-500">Classe: {p.fpc_data?.execution_class || '-'}</div>
            </div>
            <Shield className="h-5 w-5 text-zinc-500" />
          </div>
        ))}
        {projects.length === 0 && <p className="text-center py-8 text-zinc-500">Nessun progetto FPC. Converti un preventivo per iniziare.</p>}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════
export default function TracciabilitaPage() {
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
