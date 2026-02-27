/**
 * Dashboard Page - Main authenticated area
 * Shows overview of documents, quick actions, and recent activity.
 */
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest, formatDateIT } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Badge } from '../components/ui/badge';
import {
    FileText,
    Plus,
    Receipt,
    Users,
    ChevronRight,
    Clock,
    TrendingUp,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';

const formatCurrency = (value) => {
    return new Intl.NumberFormat('it-IT', {
        style: 'currency',
        currency: 'EUR',
    }).format(value || 0);
};

const STATUS_BADGES = {
    bozza: { label: 'Bozza', color: 'bg-slate-100 text-slate-800' },
    emessa: { label: 'Emessa', color: 'bg-blue-100 text-blue-800' },
    pagata: { label: 'Pagata', color: 'bg-emerald-100 text-emerald-800' },
    scaduta: { label: 'Scaduta', color: 'bg-orange-100 text-orange-800' },
};

export default function Dashboard() {
    const { user, loading } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [stats, setStats] = useState({
        totalInvoices: 0,
        totalClients: 0,
        recentInvoices: [],
        monthlyTotal: 0,
    });
    const [loadingStats, setLoadingStats] = useState(true);

    // Get user from context or location state
    const currentUser = user || location.state?.user;

    useEffect(() => {
        const fetchStats = async () => {
            try {
                // Fetch recent invoices
                const invoicesData = await apiRequest('/invoices/?limit=5');
                const clientsData = await apiRequest('/clients/?limit=1');
                
                // Calculate monthly total
                const currentYear = new Date().getFullYear();
                const allInvoices = await apiRequest(`/invoices/?year=${currentYear}&limit=100`);
                const monthlyTotal = allInvoices.invoices
                    .filter(inv => inv.status === 'pagata')
                    .reduce((sum, inv) => sum + (inv.totals?.total_document || 0), 0);

                setStats({
                    totalInvoices: invoicesData.total,
                    totalClients: clientsData.total,
                    recentInvoices: invoicesData.invoices,
                    monthlyTotal,
                });
            } catch (error) {
                console.error('Error loading stats:', error);
            } finally {
                setLoadingStats(false);
            }
        };

        if (currentUser) {
            fetchStats();
        }
    }, [currentUser]);

    if (loading && !location.state?.user) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="w-8 h-8 loading-spinner" />
                </div>
            </DashboardLayout>
        );
    }

    if (!currentUser) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="w-8 h-8 loading-spinner" />
                </div>
            </DashboardLayout>
        );
    }

    const quickActions = [
        {
            icon: Receipt,
            label: 'Nuova Fattura',
            description: 'Crea un nuovo documento',
            action: () => navigate('/invoices/new'),
            testId: 'quick-action-new-invoice',
        },
        {
            icon: Users,
            label: 'Nuovo Cliente',
            description: 'Aggiungi all\'anagrafica',
            action: () => navigate('/clients'),
            testId: 'quick-action-new-client',
        },
        {
            icon: FileText,
            label: 'Documenti Legali',
            description: 'Genera con AI (Coming soon)',
            action: () => navigate('/documents'),
            testId: 'quick-action-documents',
            disabled: true,
        },
    ];

    return (
        <DashboardLayout>
            {/* Header */}
            <div className="mb-8">
                <h1 className="font-serif text-3xl font-bold text-slate-900 mb-2">
                    Bentornato, {currentUser.name?.split(' ')[0]}
                </h1>
                <p className="text-slate-600">
                    Ecco una panoramica della tua attività.
                </p>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <Card className="border-slate-200">
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-slate-500">Documenti</p>
                                <p className="text-3xl font-bold text-slate-900">
                                    {loadingStats ? '-' : stats.totalInvoices}
                                </p>
                            </div>
                            <div className="w-12 h-12 flex items-center justify-center bg-blue-100 rounded-lg">
                                <Receipt className="h-6 w-6 text-blue-600" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200">
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-slate-500">Clienti</p>
                                <p className="text-3xl font-bold text-slate-900">
                                    {loadingStats ? '-' : stats.totalClients}
                                </p>
                            </div>
                            <div className="w-12 h-12 flex items-center justify-center bg-purple-100 rounded-lg">
                                <Users className="h-6 w-6 text-purple-600" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200">
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-slate-500">Fatturato Anno</p>
                                <p className="text-2xl font-bold text-slate-900">
                                    {loadingStats ? '-' : formatCurrency(stats.monthlyTotal)}
                                </p>
                            </div>
                            <div className="w-12 h-12 flex items-center justify-center bg-emerald-100 rounded-lg">
                                <TrendingUp className="h-6 w-6 text-emerald-600" />
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {quickActions.map((action) => (
                    <Card
                        key={action.label}
                        data-testid={action.testId}
                        className={`group border-slate-200 transition-all duration-300 ${
                            action.disabled 
                                ? 'opacity-50 cursor-not-allowed' 
                                : 'cursor-pointer hover:shadow-md hover:border-slate-300'
                        }`}
                        onClick={action.disabled ? undefined : action.action}
                    >
                        <CardContent className="p-6">
                            <div className="flex items-start justify-between">
                                <div className={`w-12 h-12 flex items-center justify-center rounded-lg transition-colors duration-300 ${
                                    action.disabled 
                                        ? 'bg-slate-100 text-slate-400' 
                                        : 'bg-[#0055FF] text-white group-hover:bg-[#0044CC]'
                                }`}>
                                    <action.icon className="h-6 w-6" strokeWidth={1.5} />
                                </div>
                                {!action.disabled && (
                                    <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-slate-600 transition-colors" />
                                )}
                            </div>
                            <h3 className="mt-4 font-semibold text-slate-900">
                                {action.label}
                            </h3>
                            <p className="text-sm text-slate-500">
                                {action.description}
                            </p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Recent Invoices */}
            <Card className="border-slate-200">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="font-serif text-xl">Documenti Recenti</CardTitle>
                        <CardDescription>Le tue ultime fatture e preventivi</CardDescription>
                    </div>
                    <Button
                        data-testid="btn-view-all-invoices"
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate('/invoices')}
                    >
                        Vedi tutti
                    </Button>
                </CardHeader>
                <CardContent>
                    {loadingStats ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="w-6 h-6 loading-spinner" />
                        </div>
                    ) : stats.recentInvoices.length === 0 ? (
                        <div className="text-center py-12">
                            <Receipt className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                            <p className="text-slate-500">Nessun documento ancora</p>
                            <Button
                                data-testid="btn-create-first-invoice"
                                className="mt-4 bg-[#0055FF] text-white hover:bg-[#0044CC]"
                                onClick={() => navigate('/invoices/new')}
                            >
                                <Plus className="h-4 w-4 mr-2" />
                                Crea il primo documento
                            </Button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {stats.recentInvoices.map((inv) => (
                                <div
                                    key={inv.invoice_id}
                                    data-testid={`recent-invoice-${inv.invoice_id}`}
                                    className="flex items-center justify-between p-4 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors cursor-pointer"
                                    onClick={() => navigate(`/invoices/${inv.invoice_id}`)}
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 flex items-center justify-center bg-slate-100 rounded-lg">
                                            <Receipt className="h-5 w-5 text-slate-600" strokeWidth={1.5} />
                                        </div>
                                        <div>
                                            <p className="font-medium text-slate-900">
                                                {inv.document_number}
                                            </p>
                                            <p className="text-sm text-slate-500">
                                                {inv.client_name}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <div className="text-right">
                                            <p className="font-medium text-slate-900">
                                                {formatCurrency(inv.totals?.total_document)}
                                            </p>
                                            <div className="flex items-center gap-2 text-sm text-slate-500">
                                                <Clock className="h-3 w-3" />
                                                {formatDateIT(inv.issue_date)}
                                            </div>
                                        </div>
                                        <Badge className={STATUS_BADGES[inv.status]?.color || 'bg-slate-100'}>
                                            {STATUS_BADGES[inv.status]?.label || inv.status}
                                        </Badge>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </DashboardLayout>
    );
}
