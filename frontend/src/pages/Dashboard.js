/**
 * Dashboard Page - Main authenticated area
 * Shows overview of documents, quick actions, and recent activity.
 */
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import {
    Scale,
    FileText,
    MessageSquare,
    Plus,
    LogOut,
    User,
    FolderOpen,
    Clock,
    ChevronRight,
    Sparkles,
    Archive,
} from 'lucide-react';

export default function Dashboard() {
    const { user, logout, loading, checkAuth } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [isAuthenticated, setIsAuthenticated] = useState(location.state?.user ? true : null);

    useEffect(() => {
        // If user data passed from AuthCallback, skip auth check
        if (location.state?.user) {
            setIsAuthenticated(true);
            return;
        }

        const verifyAuth = async () => {
            if (!user && !loading) {
                try {
                    await checkAuth();
                } catch (error) {
                    navigate('/');
                }
            }
        };

        verifyAuth();
    }, [user, loading, checkAuth, navigate, location.state]);

    // Get user from context or location state
    const currentUser = user || location.state?.user;

    if (loading && !location.state?.user) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 loading-spinner" />
            </div>
        );
    }

    if (!currentUser) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 loading-spinner" />
            </div>
        );
    }

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const quickActions = [
        {
            icon: FileText,
            label: 'Nuovo Documento',
            description: 'Genera un documento legale',
            action: () => navigate('/documents/new'),
            testId: 'quick-action-new-doc',
        },
        {
            icon: MessageSquare,
            label: 'Assistente AI',
            description: 'Fai una domanda legale',
            action: () => navigate('/chat'),
            testId: 'quick-action-chat',
        },
        {
            icon: FolderOpen,
            label: 'Archivio',
            description: 'Visualizza i tuoi documenti',
            action: () => navigate('/documents'),
            testId: 'quick-action-archive',
        },
    ];

    const recentDocuments = [
        { id: 1, title: 'Contratto di Locazione', type: 'contratto', date: '2 ore fa' },
        { id: 2, title: 'Lettera di Diffida', type: 'lettera', date: 'Ieri' },
        { id: 3, title: 'Procura Generale', type: 'procura', date: '3 giorni fa' },
    ];

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Sidebar */}
            <aside className="fixed left-0 top-0 h-screen w-64 bg-slate-900 text-slate-300 border-r border-slate-800 z-50">
                <div className="p-6">
                    <div className="flex items-center gap-2 mb-10">
                        <Scale className="h-7 w-7 text-white" strokeWidth={1.5} />
                        <span className="font-serif text-lg font-bold text-white">
                            Norma Facile
                        </span>
                    </div>

                    <nav className="space-y-1">
                        <a
                            href="/dashboard"
                            data-testid="nav-dashboard"
                            className="flex items-center gap-3 px-4 py-3 rounded-md bg-white text-slate-900 font-medium shadow-sm"
                        >
                            <Sparkles className="h-5 w-5" strokeWidth={1.5} />
                            Dashboard
                        </a>
                        <a
                            href="/documents"
                            data-testid="nav-documents"
                            className="flex items-center gap-3 px-4 py-3 rounded-md transition-colors hover:text-white hover:bg-white/10"
                        >
                            <FileText className="h-5 w-5" strokeWidth={1.5} />
                            Documenti
                        </a>
                        <a
                            href="/chat"
                            data-testid="nav-chat"
                            className="flex items-center gap-3 px-4 py-3 rounded-md transition-colors hover:text-white hover:bg-white/10"
                        >
                            <MessageSquare className="h-5 w-5" strokeWidth={1.5} />
                            Assistente
                        </a>
                        <a
                            href="/archive"
                            data-testid="nav-archive"
                            className="flex items-center gap-3 px-4 py-3 rounded-md transition-colors hover:text-white hover:bg-white/10"
                        >
                            <Archive className="h-5 w-5" strokeWidth={1.5} />
                            Archivio
                        </a>
                    </nav>
                </div>

                {/* User menu at bottom */}
                <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-800">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <button
                                data-testid="user-menu-btn"
                                className="flex items-center gap-3 w-full p-2 rounded-md hover:bg-white/10 transition-colors"
                            >
                                <Avatar className="h-9 w-9">
                                    <AvatarImage src={currentUser.picture} alt={currentUser.name} />
                                    <AvatarFallback className="bg-amber-700 text-white text-sm">
                                        {currentUser.name?.charAt(0) || 'U'}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex-1 text-left">
                                    <p className="text-sm font-medium text-white truncate">
                                        {currentUser.name}
                                    </p>
                                    <p className="text-xs text-slate-400 truncate">
                                        {currentUser.email}
                                    </p>
                                </div>
                            </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-56">
                            <DropdownMenuLabel>Il mio account</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem data-testid="menu-profile">
                                <User className="mr-2 h-4 w-4" />
                                Profilo
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                data-testid="menu-logout"
                                onClick={handleLogout}
                                className="text-red-600"
                            >
                                <LogOut className="mr-2 h-4 w-4" />
                                Esci
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </aside>

            {/* Main Content */}
            <main className="ml-64 p-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="font-serif text-3xl font-bold text-slate-900 mb-2">
                        Bentornato, {currentUser.name?.split(' ')[0]}
                    </h1>
                    <p className="text-slate-600">
                        Ecco una panoramica della tua attività.
                    </p>
                </div>

                {/* Quick Actions */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    {quickActions.map((action) => (
                        <Card
                            key={action.label}
                            data-testid={action.testId}
                            className="group cursor-pointer border-slate-200 hover:shadow-md hover:border-slate-300 transition-all duration-300"
                            onClick={action.action}
                        >
                            <CardContent className="p-6">
                                <div className="flex items-start justify-between">
                                    <div className="w-12 h-12 flex items-center justify-center bg-slate-900 text-white rounded-lg group-hover:bg-amber-700 transition-colors duration-300">
                                        <action.icon className="h-6 w-6" strokeWidth={1.5} />
                                    </div>
                                    <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-slate-600 transition-colors" />
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

                {/* Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Recent Documents */}
                    <Card className="lg:col-span-2 border-slate-200">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="font-serif text-xl">Documenti Recenti</CardTitle>
                                <CardDescription>I tuoi ultimi documenti generati</CardDescription>
                            </div>
                            <Button
                                data-testid="btn-view-all-docs"
                                variant="ghost"
                                size="sm"
                                onClick={() => navigate('/documents')}
                            >
                                Vedi tutti
                            </Button>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {recentDocuments.map((doc) => (
                                    <div
                                        key={doc.id}
                                        data-testid={`recent-doc-${doc.id}`}
                                        className="flex items-center justify-between p-4 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors cursor-pointer"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 flex items-center justify-center bg-slate-100 rounded-lg">
                                                <FileText className="h-5 w-5 text-slate-600" strokeWidth={1.5} />
                                            </div>
                                            <div>
                                                <p className="font-medium text-slate-900">{doc.title}</p>
                                                <p className="text-sm text-slate-500 capitalize">{doc.type}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2 text-sm text-slate-500">
                                            <Clock className="h-4 w-4" />
                                            {doc.date}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {recentDocuments.length === 0 && (
                                <div className="text-center py-12">
                                    <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                                    <p className="text-slate-500">Nessun documento ancora</p>
                                    <Button
                                        data-testid="btn-create-first-doc"
                                        className="mt-4 bg-slate-900 text-white hover:bg-slate-800"
                                        onClick={() => navigate('/documents/new')}
                                    >
                                        <Plus className="h-4 w-4 mr-2" />
                                        Crea il tuo primo documento
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Storage Usage */}
                    <Card className="border-slate-200">
                        <CardHeader>
                            <CardTitle className="font-serif text-xl">Spazio di Archiviazione</CardTitle>
                            <CardDescription>Utilizzo del tuo piano</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <div>
                                    <div className="flex justify-between text-sm mb-2">
                                        <span className="text-slate-600">3 di 100 documenti</span>
                                        <span className="font-medium text-slate-900">3%</span>
                                    </div>
                                    <Progress value={3} className="h-2" />
                                </div>
                                <div className="pt-4 border-t border-slate-200">
                                    <p className="text-sm text-slate-600 mb-4">
                                        Piano attuale: <span className="font-medium text-slate-900">Gratuito</span>
                                    </p>
                                    <Button
                                        data-testid="btn-upgrade"
                                        variant="outline"
                                        className="w-full border-amber-700 text-amber-700 hover:bg-amber-50"
                                    >
                                        Passa a Pro
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </main>
        </div>
    );
}
