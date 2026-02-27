/**
 * QuickActionFAB — Floating Action Button "Nuovo" with expanding menu.
 */
import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Ruler, ClipboardList, Users, X } from 'lucide-react';

const actions = [
    { label: 'Nuovo Rilievo', icon: Ruler, path: '/rilievi/new', color: 'bg-amber-500 hover:bg-amber-600' },
    { label: 'Nuovo Preventivo', icon: ClipboardList, path: '/preventivi/new', color: 'bg-emerald-500 hover:bg-emerald-600' },
    { label: 'Nuovo Cliente', icon: Users, path: '/clients', color: 'bg-violet-500 hover:bg-violet-600' },
];

export default function QuickActionFAB() {
    const [open, setOpen] = useState(false);
    const navigate = useNavigate();
    const ref = useRef(null);

    useEffect(() => {
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    return (
        <div ref={ref} className="fixed bottom-8 right-8 z-50 flex flex-col-reverse items-end gap-3" data-testid="quick-action-fab">
            {/* Action items */}
            {open && actions.map((a, i) => (
                <button
                    key={a.path}
                    data-testid={`fab-action-${i}`}
                    onClick={() => { navigate(a.path); setOpen(false); }}
                    className={`flex items-center gap-3 pl-4 pr-5 py-2.5 rounded-full text-white shadow-lg ${a.color} transition-all duration-200 opacity-0 translate-y-2`}
                    style={{
                        animation: `fabSlideIn 0.2s ease-out ${i * 0.06}s forwards`,
                    }}
                >
                    <a.icon className="h-4 w-4" />
                    <span className="text-sm font-medium whitespace-nowrap">{a.label}</span>
                </button>
            ))}

            {/* Main FAB */}
            <button
                data-testid="fab-main-btn"
                onClick={() => setOpen(v => !v)}
                className={`w-14 h-14 rounded-full shadow-xl flex items-center justify-center transition-all duration-300 ${
                    open
                        ? 'bg-slate-700 hover:bg-slate-800 rotate-45'
                        : 'bg-[#0055FF] hover:bg-[#0044CC] hover:scale-110 hover:shadow-blue-300/50'
                }`}
            >
                {open ? <X className="h-6 w-6 text-white" /> : <Plus className="h-6 w-6 text-white" />}
            </button>

            <style>{`
                @keyframes fabSlideIn {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
