/**
 * Dashboard Layout Component
 * Reusable sidebar layout for authenticated pages.
 */
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
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
    LogOut,
    User,
    Sparkles,
    Receipt,
    Users,
    Settings,
    Ruler,
    Package,
    Shield,
    HardHat,
    Warehouse,
} from 'lucide-react';

const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: Sparkles },
    { path: '/invoices', label: 'Fatturazione', icon: Receipt },
    { path: '/clients', label: 'Clienti', icon: Users },
    { path: '/rilievi', label: 'Rilievi', icon: Ruler },
    { path: '/distinte', label: 'Distinte', icon: Package },
    { path: '/catalogo', label: 'Catalogo Profili', icon: Warehouse },
    { path: '/certificazioni', label: 'Certificazioni CE', icon: Shield },
    { path: '/sicurezza', label: 'Sicurezza (POS)', icon: HardHat },
    { path: '/settings', label: 'Impostazioni', icon: Settings },
];

export default function DashboardLayout({ children }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const isActive = (path) => {
        if (path === '/dashboard') return location.pathname === '/dashboard';
        return location.pathname.startsWith(path);
    };

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Sidebar */}
            <aside className="fixed left-0 top-0 h-screen w-64 bg-[#1E293B] text-slate-300 border-r border-slate-700 z-50">
                <div className="p-6">
                    <div className="flex items-center gap-2 mb-10">
                        <Scale className="h-7 w-7 text-[#0055FF]" strokeWidth={1.5} />
                        <span className="font-sans text-lg font-bold text-white">
                            Norma Facile
                        </span>
                    </div>

                    <nav className="space-y-1">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            const active = isActive(item.path);
                            return (
                                <a
                                    key={item.path}
                                    href={item.path}
                                    data-testid={`nav-${item.path.slice(1)}`}
                                    className={`flex items-center gap-3 px-4 py-3 rounded-md transition-colors ${
                                        active
                                            ? 'bg-[#0055FF] text-white font-medium'
                                            : 'hover:text-white hover:bg-white/10'
                                    }`}
                                >
                                    <Icon className="h-5 w-5" strokeWidth={1.5} />
                                    {item.label}
                                </a>
                            );
                        })}
                    </nav>
                </div>

                {/* User menu at bottom */}
                <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-700">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <button
                                data-testid="user-menu-btn"
                                className="flex items-center gap-3 w-full p-2 rounded-md hover:bg-white/10 transition-colors"
                            >
                                <Avatar className="h-9 w-9">
                                    <AvatarImage src={user?.picture} alt={user?.name} />
                                    <AvatarFallback className="bg-[#0055FF] text-white text-sm">
                                        {user?.name?.charAt(0) || 'U'}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex-1 text-left">
                                    <p className="text-sm font-medium text-white truncate">
                                        {user?.name}
                                    </p>
                                    <p className="text-xs text-slate-400 truncate">
                                        {user?.email}
                                    </p>
                                </div>
                            </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-56">
                            <DropdownMenuLabel>Il mio account</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                data-testid="menu-profile"
                                onClick={() => navigate('/settings')}
                            >
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
                {children}
            </main>
        </div>
    );
}
