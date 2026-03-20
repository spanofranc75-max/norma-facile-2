import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../../lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Users, UserPlus, Trash2, Shield, Loader2 } from 'lucide-react';
import { useConfirm } from '../ConfirmProvider';

const ROLE_OPTIONS = [
    { value: 'ufficio_tecnico', label: 'Ufficio Tecnico', desc: 'Commesse, FPC, Saldatori, Qualita' },
    { value: 'officina', label: 'Officina', desc: 'Solo produzione, no finanza' },
    { value: 'amministrazione', label: 'Amministrazione', desc: 'Fatture, costi, clienti, no WPS' },
    { value: 'guest', label: 'In Attesa', desc: 'Nessun accesso ai dati' },
];

const ROLE_COLORS = {
    admin: 'bg-lime-100 text-lime-800 border-lime-300',
    ufficio_tecnico: 'bg-blue-100 text-blue-800 border-blue-300',
    officina: 'bg-amber-100 text-amber-800 border-amber-300',
    amministrazione: 'bg-violet-100 text-violet-800 border-violet-300',
    guest: 'bg-slate-100 text-slate-600 border-slate-300',
};

export default function TeamTab() {
    const confirm = useConfirm();
    const [members, setMembers] = useState([]);
    const [invites, setInvites] = useState([]);
    const [roleLabels, setRoleLabels] = useState({});
    const [loading, setLoading] = useState(true);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteName, setInviteName] = useState('');
    const [inviteRole, setInviteRole] = useState('officina');
    const [sending, setSending] = useState(false);

    const fetchTeam = useCallback(async () => {
        try {
            const data = await apiRequest('/team/members');
            setMembers(data.members || []);
            setInvites(data.invites || []);
            setRoleLabels(data.roles || {});
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchTeam(); }, [fetchTeam]);

    const handleInvite = async () => {
        if (!inviteEmail) { toast.error('Inserisci un\'email'); return; }
        setSending(true);
        try {
            await apiRequest('/team/invite', { method: 'POST', body: { email: inviteEmail, role: inviteRole, name: inviteName } });
            toast.success(`Invito inviato a ${inviteEmail}`);
            setInviteEmail(''); setInviteName('');
            fetchTeam();
        } catch (e) { toast.error(e.message); }
        finally { setSending(false); }
    };

    const handleChangeRole = async (userId, newRole) => {
        try {
            await apiRequest(`/team/members/${userId}/role`, { method: 'PUT', body: { role: newRole } });
            toast.success('Ruolo aggiornato');
            fetchTeam();
        } catch (e) { toast.error(e.message); }
    };

    const handleRemoveMember = async (userId) => {
        if (!(await confirm('Sei sicuro di voler rimuovere questo membro?'))) return;
        try {
            await apiRequest(`/team/members/${userId}`, { method: 'DELETE' });
            toast.success('Membro rimosso');
            fetchTeam();
        } catch (e) { toast.error(e.message); }
    };

    const handleRevokeInvite = async (inviteId) => {
        try {
            await apiRequest(`/team/invites/${inviteId}`, { method: 'DELETE' });
            toast.success('Invito revocato');
            fetchTeam();
        } catch (e) { toast.error(e.message); }
    };

    return (
        <Card className="border-gray-200">
            <CardHeader className="bg-slate-800 border-b border-gray-200 rounded-t-lg">
                <CardTitle className="text-white flex items-center gap-2">
                    <Users className="h-5 w-5" /> Gestione Team
                </CardTitle>
                <CardDescription className="text-slate-300">
                    Invita i dipendenti e assegna i ruoli. Quando faranno login con Google, avranno i permessi corretti.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
                {/* Invite form */}
                <div className="border border-blue-200 bg-blue-50/30 rounded-lg p-4 space-y-3">
                    <h3 className="text-sm font-bold text-blue-800 flex items-center gap-1.5">
                        <UserPlus className="h-4 w-4" /> Invita Nuovo Membro
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                        <Input placeholder="Email" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} className="text-xs h-9" data-testid="invite-email" />
                        <Input placeholder="Nome (opzionale)" value={inviteName} onChange={e => setInviteName(e.target.value)} className="text-xs h-9" />
                        <Select value={inviteRole} onValueChange={setInviteRole}>
                            <SelectTrigger className="h-9 text-xs" data-testid="invite-role"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {ROLE_OPTIONS.map(r => (
                                    <SelectItem key={r.value} value={r.value} className="text-xs">{r.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Button onClick={handleInvite} disabled={sending} className="h-9 bg-blue-600 hover:bg-blue-700 text-white text-xs" data-testid="btn-invite">
                            {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <UserPlus className="h-3.5 w-3.5 mr-1" />}
                            Invita
                        </Button>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {ROLE_OPTIONS.map(r => (
                            <div key={r.value} className="bg-white border rounded px-2 py-1.5">
                                <p className={`text-[10px] font-bold border rounded-full px-1.5 py-0.5 inline-block ${ROLE_COLORS[r.value]}`}>{r.label}</p>
                                <p className="text-[9px] text-slate-400 mt-0.5">{r.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Pending invites */}
                {invites.length > 0 && (
                    <div>
                        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Inviti in Attesa ({invites.length})</h3>
                        <div className="space-y-1.5">
                            {invites.map(inv => (
                                <div key={inv.invite_id} className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-lg px-3 py-2" data-testid={`invite-${inv.invite_id}`}>
                                    <div>
                                        <p className="text-xs font-medium text-slate-700">{inv.email} {inv.name && <span className="text-slate-400">({inv.name})</span>}</p>
                                        <span className={`text-[9px] font-bold border rounded-full px-1.5 py-0.5 ${ROLE_COLORS[inv.role]}`}>{roleLabels[inv.role] || inv.role}</span>
                                    </div>
                                    <button onClick={() => handleRevokeInvite(inv.invite_id)} className="text-slate-400 hover:text-red-500 p-1" title="Revoca invito">
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Active members */}
                <div>
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Membri Attivi ({members.length})</h3>
                    {loading ? (
                        <p className="text-xs text-slate-400 flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Caricamento...</p>
                    ) : (
                        <div className="space-y-1.5">
                            {members.map(m => (
                                <div key={m.user_id} className="flex items-center justify-between bg-white border rounded-lg px-3 py-2" data-testid={`member-${m.user_id}`}>
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">
                                            {m.name?.charAt(0) || m.email?.charAt(0) || '?'}
                                        </div>
                                        <div>
                                            <p className="text-xs font-medium text-slate-700">{m.name || m.email}</p>
                                            <p className="text-[10px] text-slate-400">{m.email}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {m.role === 'admin' ? (
                                            <span className={`text-[9px] font-bold border rounded-full px-2 py-0.5 ${ROLE_COLORS.admin}`}>
                                                <Shield className="h-2.5 w-2.5 inline mr-0.5" /> Admin
                                            </span>
                                        ) : (
                                            <>
                                                <Select value={m.role || 'guest'} onValueChange={val => handleChangeRole(m.user_id, val)}>
                                                    <SelectTrigger className="h-7 text-[10px] w-32 border-slate-200"><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        {ROLE_OPTIONS.map(r => (
                                                            <SelectItem key={r.value} value={r.value} className="text-xs">{r.label}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <button onClick={() => handleRemoveMember(m.user_id)} className="text-slate-400 hover:text-red-500 p-1" title="Rimuovi">
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
