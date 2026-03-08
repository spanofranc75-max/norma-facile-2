/**
 * Activity Log (Audit Trail) — Registro delle attivita utente
 * Pagina admin per consultare chi ha fatto cosa e quando.
 */
import { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import { apiRequest } from '../lib/utils';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import {
  Search, ChevronLeft, ChevronRight, Filter, History, Users, Activity,
  FileText, RefreshCw,
} from 'lucide-react';

const ACTION_COLORS = {
  create: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  update: 'bg-blue-100 text-blue-700 border-blue-200',
  delete: 'bg-red-100 text-red-700 border-red-200',
  import: 'bg-amber-100 text-amber-700 border-amber-200',
  export: 'bg-purple-100 text-purple-700 border-purple-200',
  status_change: 'bg-orange-100 text-orange-700 border-orange-200',
  email_sent: 'bg-cyan-100 text-cyan-700 border-cyan-200',
};

const PAGE_SIZE = 30;

export default function ActivityLogPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [entityType, setEntityType] = useState('');
  const [action, setAction] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Labels from backend
  const [actionLabels, setActionLabels] = useState({});
  const [entityLabels, setEntityLabels] = useState({});
  const [entityTypes, setEntityTypes] = useState([]);
  const [actionTypes, setActionTypes] = useState([]);

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiRequest('/activity-log/stats');
      if (data) {
        setStats(data);
        setActionLabels(data.action_labels || {});
        setEntityLabels(data.entity_labels || {});
        setEntityTypes(data.entity_types || []);
        setActionTypes(data.action_types || []);
      }
    } catch { /* ignore */ }
  }, []);

  const fetchLog = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('skip', String((page - 1) * PAGE_SIZE));
      params.set('limit', String(PAGE_SIZE));
      if (search) params.set('search', search);
      if (entityType) params.set('entity_type', entityType);
      if (action) params.set('action', action);
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      const data = await apiRequest(`/activity-log?${params.toString()}`);
      setItems(data?.items || []);
      setTotal(data?.total || 0);
    } catch { setItems([]); setTotal(0); }
    setLoading(false);
  }, [page, search, entityType, action, dateFrom, dateTo]);

  useEffect(() => { fetchStats(); }, [fetchStats]);
  useEffect(() => { fetchLog(); }, [fetchLog]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const resetFilters = () => {
    setSearch(''); setEntityType(''); setAction(''); setDateFrom(''); setDateTo(''); setPage(1);
  };

  const formatTimestamp = (ts) => {
    if (!ts) return '-';
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })
        + ' ' + d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    } catch { return ts; }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="activity-log-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900" data-testid="activity-log-title">
              Registro Attivita
            </h1>
            <p className="text-sm text-slate-500 mt-1">Audit trail completo di tutte le operazioni</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => { fetchStats(); fetchLog(); }} data-testid="refresh-log-btn">
            <RefreshCw className="h-4 w-4 mr-1" /> Aggiorna
          </Button>
        </div>

        {/* Stats cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4" data-testid="activity-stats">
            <StatCard icon={Activity} label="Oggi" value={stats.today} color="text-blue-600 bg-blue-50" />
            <StatCard icon={History} label="Ultima settimana" value={stats.this_week} color="text-emerald-600 bg-emerald-50" />
            <StatCard icon={FileText} label="Totale registri" value={stats.total} color="text-slate-600 bg-slate-50" />
            <StatCard icon={Users} label="Utenti attivi (7gg)" value={stats.top_users?.length || 0} color="text-violet-600 bg-violet-50" />
          </div>
        )}

        {/* Filters */}
        <div className="bg-white border border-slate-200 rounded-lg p-4" data-testid="activity-filters">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="h-4 w-4 text-slate-500" />
            <span className="text-sm font-medium text-slate-700">Filtri</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <Input
              placeholder="Cerca..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              data-testid="activity-search-input"
            />
            <Select value={entityType} onValueChange={(v) => { setEntityType(v === '__all__' ? '' : v); setPage(1); }}>
              <SelectTrigger data-testid="entity-type-filter">
                <SelectValue placeholder="Tipo entita" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Tutte le entita</SelectItem>
                {entityTypes.map(t => (
                  <SelectItem key={t} value={t}>{entityLabels[t] || t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={action} onValueChange={(v) => { setAction(v === '__all__' ? '' : v); setPage(1); }}>
              <SelectTrigger data-testid="action-filter">
                <SelectValue placeholder="Azione" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Tutte le azioni</SelectItem>
                {actionTypes.map(a => (
                  <SelectItem key={a} value={a}>{actionLabels[a] || a}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} data-testid="date-from-filter" />
            <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} data-testid="date-to-filter" />
          </div>
          {(search || entityType || action || dateFrom || dateTo) && (
            <Button variant="ghost" size="sm" onClick={resetFilters} className="mt-2 text-xs" data-testid="reset-filters-btn">
              Resetta filtri
            </Button>
          )}
        </div>

        {/* Table */}
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden" data-testid="activity-table-container">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead className="w-[160px]">Data/Ora</TableHead>
                <TableHead className="w-[160px]">Utente</TableHead>
                <TableHead className="w-[110px]">Azione</TableHead>
                <TableHead className="w-[130px]">Tipo</TableHead>
                <TableHead>Etichetta / ID</TableHead>
                <TableHead>Dettagli</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={6} className="text-center py-12 text-slate-400">Caricamento...</TableCell></TableRow>
              ) : items.length === 0 ? (
                <TableRow><TableCell colSpan={6} className="text-center py-12 text-slate-400">Nessuna attivita trovata</TableCell></TableRow>
              ) : items.map((item, idx) => (
                <TableRow key={idx} className="hover:bg-slate-50/50" data-testid={`activity-row-${idx}`}>
                  <TableCell className="text-xs text-slate-600 font-mono">{formatTimestamp(item.timestamp)}</TableCell>
                  <TableCell className="text-sm">{item.user_name || item.user_email || '-'}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={`text-[10px] font-medium ${ACTION_COLORS[item.action] || 'bg-slate-100 text-slate-600'}`}>
                      {actionLabels[item.action] || item.action}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-slate-600">{entityLabels[item.entity_type] || item.entity_type}</TableCell>
                  <TableCell className="text-sm font-medium text-slate-800 max-w-[200px] truncate">
                    {item.label || item.entity_id || '-'}
                  </TableCell>
                  <TableCell className="text-xs text-slate-500 max-w-[200px] truncate">
                    {item.details && Object.keys(item.details).length > 0
                      ? Object.entries(item.details).map(([k,v]) => `${k}: ${v}`).join(', ')
                      : '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50/50">
              <span className="text-xs text-slate-500">
                {total} registri totali - Pagina {page} di {totalPages}
              </span>
              <div className="flex gap-1">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)} data-testid="prev-page-btn">
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} data-testid="next-page-btn">
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className={`rounded-lg border p-4 flex items-center gap-3 ${color}`}>
      <Icon className="h-5 w-5" />
      <div>
        <p className="text-2xl font-bold">{value ?? 0}</p>
        <p className="text-xs opacity-70">{label}</p>
      </div>
    </div>
  );
}
