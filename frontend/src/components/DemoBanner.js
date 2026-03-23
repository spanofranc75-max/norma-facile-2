/**
 * DemoBanner — Persistent banner when in demo mode.
 * Shows at top of every page. Non-invasive but always visible.
 */
import { useAuth } from '../contexts/AuthContext';
import { FlaskConical } from 'lucide-react';

export default function DemoBanner() {
    const { user } = useAuth();

    if (!user?.is_demo) return null;

    return (
        <div
            className="bg-amber-500 text-white text-center py-1.5 px-4 text-xs font-semibold flex items-center justify-center gap-2 sticky top-0 z-50"
            data-testid="demo-banner"
        >
            <FlaskConical className="h-3.5 w-3.5" />
            Ambiente Demo — Dati simulati, nessuna azione esterna reale
        </div>
    );
}
