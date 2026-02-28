/**
 * FPCProjectPage — Single FPC Project Detail with CE Label workflow
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, Shield, AlertTriangle, CheckCircle, User, FileText, Package, ChevronDown } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
function getHeaders() {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

export default function FPCProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [welders, setWelders] = useState([]);
  const [batches, setBatches] = useState([]);
  const [ceCheck, setCeCheck] = useState(null);

  const load = useCallback(async () => {
    const [pRes, wRes, bRes] = await Promise.all([
      fetch(`${API}/api/fpc/projects/${projectId}`, { headers: getHeaders() }),
      fetch(`${API}/api/fpc/welders`, { headers: getHeaders() }),
      fetch(`${API}/api/fpc/batches`, { headers: getHeaders() }),
    ]);
    if (pRes.ok) setProject(await pRes.json());
    if (wRes.ok) setWelders(await wRes.json());
    if (bRes.ok) setBatches(await bRes.json());
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const checkCE = async () => {
    const r = await fetch(`${API}/api/fpc/projects/${projectId}/ce-check`, { headers: getHeaders() });
    if (r.ok) setCeCheck(await r.json());
  };

  const updateFPC = async (data) => {
    const r = await fetch(`${API}/api/fpc/projects/${projectId}/fpc`, {
      method: 'PUT', headers: getHeaders(), body: JSON.stringify(data)
    });
    if (r.ok) {
      const result = await r.json();
      if (result.warning) toast.warning(result.warning);
      else toast.success('Aggiornato');
      load();
    }
  };

  const assignBatch = async (lineIndex, batchId) => {
    const r = await fetch(`${API}/api/fpc/projects/${projectId}/assign-batch`, {
      method: 'POST', headers: getHeaders(), body: JSON.stringify({ line_index: lineIndex, batch_id: batchId })
    });
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
    const r = await fetch(`${API}/api/fpc/projects/${projectId}/generate-ce`, {
      method: 'POST', headers: getHeaders()
    });
    if (r.ok) { toast.success('Etichetta CE generata con successo!'); load(); setCeCheck(null); }
    else { const d = await r.json().catch(() => ({})); toast.error(d.detail || 'Errore generazione CE'); }
  };

  if (!project) return <div className="flex h-screen bg-zinc-950 text-white"><Sidebar /><main className="flex-1 flex items-center justify-center"><p className="text-zinc-400">Caricamento...</p></main></div>;

  const fpc = project.fpc_data || {};

  return (
    <div className="flex h-screen bg-zinc-950 text-white">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <button onClick={() => navigate('/tracciabilita')} className="flex items-center text-zinc-400 hover:text-white text-sm mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" /> Torna alla lista
          </button>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold" data-testid="project-title">
                Progetto {project.preventivo_number || project.project_id}
              </h1>
              <p className="text-zinc-400">{project.client_name} — {project.subject || 'N/A'}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${fpc.execution_class === 'EXC2' ? 'bg-amber-600/20 text-amber-400 border border-amber-600/50' : fpc.execution_class === 'EXC3' || fpc.execution_class === 'EXC4' ? 'bg-red-600/20 text-red-400 border border-red-600/50' : 'bg-blue-600/20 text-blue-400 border border-blue-600/50'}`}>
                {fpc.execution_class || 'N/A'}
              </span>
              {fpc.ce_label_generated && (
                <span className="flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-green-600/20 text-green-400 border border-green-600/50">
                  <CheckCircle className="h-4 w-4" /> CE Generato
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* LEFT: Welder & WPS */}
            <div className="space-y-4">
              {/* Welder assignment */}
              <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
                <h3 className="font-medium mb-3 flex items-center gap-2"><User className="h-4 w-4 text-amber-400" /> Saldatore Assegnato</h3>
                <select
                  data-testid="welder-select"
                  value={fpc.welder_id || ''}
                  onChange={e => updateFPC({ welder_id: e.target.value || null })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm"
                >
                  <option value="">-- Seleziona saldatore --</option>
                  {welders.map(w => (
                    <option key={w.welder_id} value={w.welder_id}>
                      {w.name} {w.qualification_level ? `(${w.qualification_level})` : ''} {w.is_expired ? '⚠ SCADUTO' : ''}
                    </option>
                  ))}
                </select>
                {project.welder_expired && (
                  <p className="text-red-400 text-xs mt-2 flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> Qualifica saldatore scaduta!</p>
                )}
              </div>

              {/* WPS */}
              <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
                <h3 className="font-medium mb-3 flex items-center gap-2"><FileText className="h-4 w-4 text-amber-400" /> WPS (Procedura di Saldatura)</h3>
                <input
                  data-testid="wps-input"
                  type="text"
                  placeholder="es. WPS-001, WPS-MAG-135"
                  value={fpc.wps_id || ''}
                  onChange={e => updateFPC({ wps_id: e.target.value || null })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm"
                />
              </div>

              {/* Controls checklist */}
              <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
                <h3 className="font-medium mb-3 flex items-center gap-2"><Shield className="h-4 w-4 text-amber-400" /> Controlli FPC</h3>
                <div className="space-y-2" data-testid="fpc-controls">
                  {(fpc.controls || []).map((c, i) => (
                    <label key={i} className={`flex items-center gap-2 p-2 rounded cursor-pointer ${c.checked ? 'bg-green-900/20' : 'hover:bg-zinc-800'}`}>
                      <input
                        type="checkbox"
                        checked={c.checked}
                        onChange={() => toggleControl(i)}
                        className="rounded border-zinc-600"
                        data-testid={`control-${c.control_type}`}
                      />
                      <span className={`text-sm ${c.checked ? 'text-green-400' : 'text-zinc-300'}`}>{c.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* RIGHT: Material assignment */}
            <div className="space-y-4">
              <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
                <h3 className="font-medium mb-3 flex items-center gap-2"><Package className="h-4 w-4 text-amber-400" /> Assegnazione Materiali</h3>
                <div className="space-y-2" data-testid="material-assignment">
                  {(project.lines || []).map((ln, i) => (
                    <div key={i} className="p-2 rounded bg-zinc-800/50 border border-zinc-700">
                      <div className="text-sm font-medium mb-1 truncate">{ln.description?.substring(0, 80) || `Riga ${i + 1}`}</div>
                      <div className="flex items-center gap-2">
                        <select
                          data-testid={`batch-select-${i}`}
                          value={ln.batch_id || ''}
                          onChange={e => e.target.value && assignBatch(i, e.target.value)}
                          className="flex-1 bg-zinc-700 border border-zinc-600 rounded px-2 py-1 text-xs"
                        >
                          <option value="">-- Assegna lotto --</option>
                          {batches.map(b => (
                            <option key={b.batch_id} value={b.batch_id}>
                              {b.heat_number} ({b.material_type}) - {b.supplier_name}
                            </option>
                          ))}
                        </select>
                        {ln.batch_id && (
                          <span className="text-xs text-green-400 whitespace-nowrap">
                            <CheckCircle className="h-3 w-3 inline mr-1" />{ln.heat_number}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                  {(project.lines || []).length === 0 && <p className="text-zinc-500 text-sm">Nessuna riga nel progetto</p>}
                </div>
              </div>

              {/* CE Label Generation */}
              <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
                <h3 className="font-medium mb-3 flex items-center gap-2"><Shield className="h-4 w-4 text-green-400" /> Generazione Etichetta CE</h3>

                {fpc.ce_label_generated ? (
                  <div className="text-center py-4">
                    <CheckCircle className="h-10 w-10 text-green-400 mx-auto mb-2" />
                    <p className="text-green-400 font-medium">Etichetta CE Generata</p>
                    <p className="text-xs text-zinc-400">{fpc.ce_label_generated_at}</p>
                  </div>
                ) : (
                  <div>
                    <Button data-testid="ce-check-btn" onClick={checkCE} variant="outline" className="w-full mb-3 border-zinc-600">
                      Verifica Requisiti CE
                    </Button>

                    {ceCheck && (
                      <div className="space-y-2 mb-3">
                        {ceCheck.ready ? (
                          <p className="text-green-400 text-sm flex items-center gap-1"><CheckCircle className="h-4 w-4" /> Tutti i requisiti soddisfatti!</p>
                        ) : (
                          ceCheck.blockers.map((b, i) => (
                            <p key={i} className="text-red-400 text-xs flex items-start gap-1">
                              <AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" /> {b}
                            </p>
                          ))
                        )}
                      </div>
                    )}

                    <Button
                      data-testid="generate-ce-btn"
                      onClick={generateCE}
                      className="w-full bg-green-600 hover:bg-green-500"
                      disabled={ceCheck && !ceCheck.ready}
                    >
                      Genera Etichetta CE
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
