/**
 * FPCProjectPage — Single FPC Project Detail with CE Label workflow
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import DashboardLayout from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, Shield, AlertTriangle, CheckCircle, User, FileText, Package, ChevronDown, Printer, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const fetchOpts = (method, body) => {
  const opts = { method: method || 'GET', credentials: 'include', headers: {} };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  return opts;
};

export default function FPCProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [welders, setWelders] = useState([]);
  const [batches, setBatches] = useState([]);
  const [ceCheck, setCeCheck] = useState(null);
  const [generatingDossier, setGeneratingDossier] = useState(false);

  const load = useCallback(async () => {
    const [pRes, wRes, bRes] = await Promise.all([
      fetch(`${API}/api/fpc/projects/${projectId}`, fetchOpts()),
      fetch(`${API}/api/fpc/welders`, fetchOpts()),
      fetch(`${API}/api/fpc/batches`, fetchOpts()),
    ]);
    if (pRes.ok) setProject(await pRes.json());
    if (wRes.ok) {
      const wData = await wRes.json();
      setWelders(Array.isArray(wData) ? wData : wData.welders || []);
    }
    if (bRes.ok) {
      const bData = await bRes.json();
      setBatches(Array.isArray(bData) ? bData : bData.batches || []);
    }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const checkCE = async () => {
    const r = await fetch(`${API}/api/fpc/projects/${projectId}/ce-check`, fetchOpts());
    if (r.ok) setCeCheck(await r.json());
  };

  const updateFPC = async (data) => {
    const r = await fetch(`${API}/api/fpc/projects/${projectId}/fpc`, fetchOpts('PUT', data));
    if (r.ok) {
      const result = await r.json();
      if (result.warning) toast.warning(result.warning);
      else toast.success('Aggiornato');
      load();
    }
  };

  const assignBatch = async (lineIndex, batchId) => {
    const r = await fetch(`${API}/api/fpc/projects/${projectId}/assign-batch`, fetchOpts('POST', { line_index: lineIndex, batch_id: batchId }));
    if (r.ok) { toast.success('Lotto assegnato'); load(); }
    else { const d = await r.json().catch(() => ({})); toast.error(d.detail || 'Errore'); }
  };

  const toggleControl = (idx) => {
    const fpc = project.fpc_data || {};
    const controls = [...(fpc.controls || [])];
    controls[idx] = { ...controls[idx], checked: !controls[idx].checked, checked_at: new Date().toISOString() };
    updateFPC({ controls });
  };

  const generateCE = async () => {
    const r = await fetch(`${API}/api/fpc/projects/${projectId}/generate-ce`, fetchOpts('POST'));
    if (r.ok) { toast.success('Etichetta CE generata con successo!'); load(); setCeCheck(null); }
    else { const d = await r.json().catch(() => ({})); toast.error(d.detail || 'Errore generazione CE'); }
  };

  const downloadDossier = async () => {
    setGeneratingDossier(true);
    try {
      const r = await fetch(`${API}/api/fpc/projects/${projectId}/dossier`, fetchOpts());
      if (!r.ok) { const d = await r.json().catch(() => ({})); toast.error(d.detail || 'Errore generazione'); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Fascicolo_Tecnico_${project?.preventivo_number || projectId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Fascicolo Tecnico scaricato!');
    } catch (e) { toast.error('Errore: ' + e.message); } finally { setGeneratingDossier(false); }
  };

  if (!project) return <DashboardLayout><div className="flex items-center justify-center h-64"><p className="text-slate-400">Caricamento...</p></div></DashboardLayout>;

  const fpc = project.fpc_data || {};

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <button onClick={() => navigate('/tracciabilita')} className="flex items-center text-slate-500 hover:text-slate-800 text-sm mb-4">
          <ArrowLeft className="h-4 w-4 mr-1" /> Torna alla lista
        </button>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold" data-testid="project-title">
              Progetto {project.preventivo_number || project.project_id}
            </h1>
            <p className="text-slate-500">{project.client_name} — {project.subject || 'N/A'}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${fpc.execution_class === 'EXC2' ? 'bg-amber-50 text-amber-700 border border-amber-200' : fpc.execution_class === 'EXC3' || fpc.execution_class === 'EXC4' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-blue-50 text-blue-700 border border-blue-200'}`}>
              {fpc.execution_class || 'N/A'}
            </span>
            {fpc.ce_label_generated && (
              <span className="flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle className="h-4 w-4" /> CE Generato
              </span>
            )}
          </div>
        </div>

        {/* BIG DOSSIER BUTTON */}
        <div className="mb-6">
          <Button
            data-testid="download-dossier-btn"
            onClick={downloadDossier}
            disabled={generatingDossier}
            className="w-full h-14 text-base bg-[#0055FF] hover:bg-[#0044CC] shadow-lg"
          >
            {generatingDossier ? (
              <><Loader2 className="h-5 w-5 mr-2 animate-spin" /> Generazione Fascicolo in corso...</>
            ) : (
              <><Printer className="h-5 w-5 mr-2" /> Stampa Fascicolo Tecnico Completo</>
            )}
          </Button>
          <p className="text-xs text-slate-400 text-center mt-1">DoP + CE Label + Certificati 3.1 + Qualifica Saldatore + Controlli FPC</p>
        </div>

        {/* VERBALE DI POSA BUTTON */}
        {project.commessa_id && (
        <div className="mb-6">
          <Button
            data-testid="verbale-posa-btn"
            onClick={() => navigate(`/verbale-posa/${project.commessa_id}`)}
            variant="outline"
            className="w-full h-12 text-base border-[#0055FF] text-[#0055FF] hover:bg-blue-50"
          >
            <FileText className="h-5 w-5 mr-2" /> Genera Verbale di Posa in Opera
          </Button>
          <p className="text-xs text-slate-400 text-center mt-1">Dichiarazione di corretta posa + foto cantiere + firma cliente</p>
        </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* LEFT: Welder & WPS */}
          <div className="space-y-4">
            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium mb-3 flex items-center gap-2"><User className="h-4 w-4 text-[#0055FF]" /> Saldatore Assegnato</h3>
              <select data-testid="welder-select" value={fpc.welder_id || ''} onChange={e => updateFPC({ welder_id: e.target.value || null })} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">-- Seleziona saldatore --</option>
                {welders.map(w => (<option key={w.welder_id} value={w.welder_id}>{w.name} {w.qualification_level ? `(${w.qualification_level})` : ''} {w.is_expired ? '-- SCADUTO' : ''}</option>))}
              </select>
              {project.welder_expired && <p className="text-red-500 text-xs mt-2 flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> Qualifica saldatore scaduta!</p>}
            </div>

            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium mb-3 flex items-center gap-2"><FileText className="h-4 w-4 text-[#0055FF]" /> WPS (Procedura di Saldatura)</h3>
              <input data-testid="wps-input" type="text" placeholder="es. WPS-001, WPS-MAG-135" value={fpc.wps_id || ''} onChange={e => updateFPC({ wps_id: e.target.value || null })} className="w-full border rounded px-3 py-2 text-sm" />
            </div>

            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium mb-3 flex items-center gap-2"><Shield className="h-4 w-4 text-[#0055FF]" /> Controlli FPC</h3>
              <div className="space-y-2" data-testid="fpc-controls">
                {(fpc.controls || []).map((c, i) => (
                  <label key={i} className={`flex items-center gap-2 p-2 rounded cursor-pointer ${c.checked ? 'bg-emerald-50' : 'hover:bg-slate-50'}`}>
                    <input type="checkbox" checked={c.checked} onChange={() => toggleControl(i)} className="rounded" data-testid={`control-${c.control_type}`} />
                    <span className={`text-sm ${c.checked ? 'text-emerald-700' : ''}`}>{c.label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT: Material assignment */}
          <div className="space-y-4">
            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium mb-3 flex items-center gap-2"><Package className="h-4 w-4 text-[#0055FF]" /> Assegnazione Materiali</h3>
              <div className="space-y-2" data-testid="material-assignment">
                {(project.lines || []).map((ln, i) => (
                  <div key={i} className="p-2 rounded bg-slate-50 border">
                    <div className="text-sm font-medium mb-1 truncate">{ln.description?.substring(0, 80) || `Riga ${i + 1}`}</div>
                    <div className="flex items-center gap-2">
                      <select data-testid={`batch-select-${i}`} value={ln.batch_id || ''} onChange={e => e.target.value && assignBatch(i, e.target.value)} className="flex-1 border rounded px-2 py-1 text-xs">
                        <option value="">-- Assegna lotto --</option>
                        {batches.map(b => (<option key={b.batch_id} value={b.batch_id}>{b.heat_number} ({b.material_type}) - {b.supplier_name}</option>))}
                      </select>
                      {ln.batch_id && <span className="text-xs text-emerald-600 whitespace-nowrap"><CheckCircle className="h-3 w-3 inline mr-1" />{ln.heat_number}</span>}
                    </div>
                  </div>
                ))}
                {(project.lines || []).length === 0 && <p className="text-slate-400 text-sm">Nessuna riga nel progetto</p>}
              </div>
            </div>

            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium mb-3 flex items-center gap-2"><Shield className="h-4 w-4 text-emerald-600" /> Generazione Etichetta CE</h3>
              {fpc.ce_label_generated ? (
                <div className="text-center py-4">
                  <CheckCircle className="h-10 w-10 text-emerald-500 mx-auto mb-2" />
                  <p className="text-emerald-700 font-medium">Etichetta CE Generata</p>
                  <p className="text-xs text-slate-400">{fpc.ce_label_generated_at}</p>
                </div>
              ) : (
                <div>
                  <Button data-testid="ce-check-btn" onClick={checkCE} variant="outline" className="w-full mb-3">Verifica Requisiti CE</Button>
                  {ceCheck && (
                    <div className="space-y-2 mb-3">
                      {ceCheck.ready ? (
                        <p className="text-emerald-600 text-sm flex items-center gap-1"><CheckCircle className="h-4 w-4" /> Tutti i requisiti soddisfatti!</p>
                      ) : (
                        ceCheck.blockers.map((b, i) => (
                          <p key={i} className="text-red-500 text-xs flex items-start gap-1"><AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" /> {b}</p>
                        ))
                      )}
                    </div>
                  )}
                  <Button data-testid="generate-ce-btn" onClick={generateCE} className="w-full bg-emerald-600 hover:bg-emerald-500" disabled={ceCheck && !ceCheck.ready}>Genera Etichetta CE</Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
