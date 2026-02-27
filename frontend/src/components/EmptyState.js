/**
 * EmptyState — Friendly empty state with inline SVG illustrations.
 * Used across all list pages for a modern "zero data" experience.
 */
import { Button } from './ui/button';
import { Plus } from 'lucide-react';

const illustrations = {
    clients: (
        <svg viewBox="0 0 200 160" fill="none" className="w-full h-full">
            <rect x="40" y="100" width="120" height="40" rx="8" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1.5" />
            <circle cx="100" cy="60" r="28" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1.5" />
            <circle cx="100" cy="52" r="10" fill="#93C5FD" />
            <path d="M80 72 C80 62 120 62 120 72" stroke="#93C5FD" strokeWidth="2" fill="none" strokeLinecap="round" />
            <circle cx="60" cy="80" r="16" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1" />
            <circle cx="60" cy="76" r="6" fill="#BFDBFE" />
            <path d="M50 86 C50 80 70 80 70 86" stroke="#BFDBFE" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            <circle cx="140" cy="80" r="16" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1" />
            <circle cx="140" cy="76" r="6" fill="#BFDBFE" />
            <path d="M130 86 C130 80 150 80 150 86" stroke="#BFDBFE" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            <line x1="70" y1="115" x2="130" y2="115" stroke="#BFDBFE" strokeWidth="2" strokeLinecap="round" />
            <line x1="80" y1="125" x2="120" y2="125" stroke="#DBEAFE" strokeWidth="2" strokeLinecap="round" />
        </svg>
    ),
    invoices: (
        <svg viewBox="0 0 200 160" fill="none" className="w-full h-full">
            <rect x="50" y="20" width="100" height="120" rx="8" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1.5" />
            <rect x="60" y="35" width="50" height="4" rx="2" fill="#93C5FD" />
            <rect x="60" y="48" width="70" height="3" rx="1.5" fill="#DBEAFE" />
            <rect x="60" y="58" width="60" height="3" rx="1.5" fill="#DBEAFE" />
            <rect x="60" y="68" width="65" height="3" rx="1.5" fill="#DBEAFE" />
            <line x1="60" y1="82" x2="140" y2="82" stroke="#BFDBFE" strokeWidth="1" strokeDasharray="4 2" />
            <rect x="60" y="92" width="40" height="3" rx="1.5" fill="#DBEAFE" />
            <rect x="110" y="90" width="30" height="8" rx="4" fill="#93C5FD" />
            <text x="118" y="97" fontSize="6" fill="white" fontWeight="bold">EUR</text>
            <rect x="60" y="108" width="80" height="20" rx="4" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1" />
            <text x="77" y="121" fontSize="8" fill="#3B82F6" fontWeight="600">TOTALE</text>
        </svg>
    ),
    rilievi: (
        <svg viewBox="0 0 200 160" fill="none" className="w-full h-full">
            <rect x="30" y="60" width="140" height="80" rx="6" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1.5" />
            <rect x="40" y="50" width="60" height="30" rx="4" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1" />
            <line x1="50" y1="90" x2="160" y2="90" stroke="#93C5FD" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="50" y1="100" x2="140" y2="100" stroke="#BFDBFE" strokeWidth="1" strokeLinecap="round" />
            <line x1="50" y1="110" x2="120" y2="110" stroke="#BFDBFE" strokeWidth="1" strokeLinecap="round" />
            <line x1="50" y1="120" x2="150" y2="120" stroke="#BFDBFE" strokeWidth="1" strokeLinecap="round" />
            {/* Ruler */}
            <rect x="110" y="20" width="70" height="12" rx="2" fill="#93C5FD" opacity="0.8" />
            {[0,1,2,3,4,5,6].map(i => (
                <line key={i} x1={115 + i * 9} y1="32" x2={115 + i * 9} y2={i % 2 === 0 ? "27" : "29"} stroke="white" strokeWidth="1" />
            ))}
            {/* Pencil */}
            <path d="M155 45 L165 55 L135 85 L125 80 Z" fill="#FBBF24" stroke="#F59E0B" strokeWidth="1" />
            <path d="M125 80 L135 85 L128 90 Z" fill="#F59E0B" />
        </svg>
    ),
    distinte: (
        <svg viewBox="0 0 200 160" fill="none" className="w-full h-full">
            {/* Stack of metal bars */}
            <rect x="30" y="100" width="140" height="14" rx="3" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1" />
            <rect x="30" y="82" width="140" height="14" rx="3" fill="#BFDBFE" stroke="#93C5FD" strokeWidth="1" />
            <rect x="30" y="64" width="140" height="14" rx="3" fill="#93C5FD" stroke="#3B82F6" strokeWidth="1" />
            {/* Weight icon */}
            <circle cx="100" cy="38" r="20" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1.5" />
            <text x="89" y="42" fontSize="12" fill="#3B82F6" fontWeight="bold">kg</text>
            {/* Dimension arrows */}
            <line x1="25" y1="64" x2="25" y2="114" stroke="#93C5FD" strokeWidth="1" />
            <polyline points="22,67 25,64 28,67" stroke="#93C5FD" strokeWidth="1" fill="none" />
            <polyline points="22,111 25,114 28,111" stroke="#93C5FD" strokeWidth="1" fill="none" />
            <line x1="30" y1="122" x2="170" y2="122" stroke="#93C5FD" strokeWidth="1" />
            <polyline points="33,119 30,122 33,125" stroke="#93C5FD" strokeWidth="1" fill="none" />
            <polyline points="167,119 170,122 167,125" stroke="#93C5FD" strokeWidth="1" fill="none" />
            <rect x="70" y="128" width="60" height="16" rx="4" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1" />
            <text x="82" y="140" fontSize="8" fill="#3B82F6" fontWeight="500">6000 mm</text>
        </svg>
    ),
    preventivi: (
        <svg viewBox="0 0 200 160" fill="none" className="w-full h-full">
            <rect x="45" y="15" width="110" height="130" rx="8" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1.5" />
            <rect x="55" y="30" width="60" height="5" rx="2.5" fill="#93C5FD" />
            <rect x="55" y="45" width="80" height="3" rx="1.5" fill="#DBEAFE" />
            <rect x="55" y="55" width="70" height="3" rx="1.5" fill="#DBEAFE" />
            <rect x="55" y="65" width="75" height="3" rx="1.5" fill="#DBEAFE" />
            <line x1="55" y1="78" x2="145" y2="78" stroke="#BFDBFE" strokeWidth="1" />
            <rect x="55" y="85" width="45" height="3" rx="1.5" fill="#DBEAFE" />
            <rect x="110" y="83" width="35" height="8" rx="4" fill="#10B981" opacity="0.8" />
            <rect x="55" y="100" width="90" height="30" rx="6" fill="#DBEAFE" stroke="#93C5FD" strokeWidth="1" />
            <text x="72" y="119" fontSize="10" fill="#3B82F6" fontWeight="bold">PREVENTIVO</text>
            {/* Checkmark */}
            <circle cx="155" cy="25" r="14" fill="#10B981" opacity="0.9" />
            <polyline points="148,25 153,30 163,20" stroke="white" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    ),
    fascicolo: (
        <svg viewBox="0 0 200 160" fill="none" className="w-full h-full">
            <rect x="40" y="30" width="120" height="110" rx="8" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="1.5" />
            <rect x="55" y="20" width="90" height="15" rx="4" fill="#93C5FD" />
            <text x="75" y="31" fontSize="8" fill="white" fontWeight="bold">FASCICOLO</text>
            {/* Folder tabs */}
            <rect x="50" y="55" width="100" height="12" rx="3" fill="#DBEAFE" stroke="#BFDBFE" strokeWidth="0.5" />
            <rect x="50" y="73" width="100" height="12" rx="3" fill="#DBEAFE" stroke="#BFDBFE" strokeWidth="0.5" />
            <rect x="50" y="91" width="100" height="12" rx="3" fill="#DBEAFE" stroke="#BFDBFE" strokeWidth="0.5" />
            <rect x="50" y="109" width="100" height="12" rx="3" fill="#DBEAFE" stroke="#BFDBFE" strokeWidth="0.5" />
            <circle cx="62" cy="61" r="3" fill="#3B82F6" />
            <circle cx="62" cy="79" r="3" fill="#10B981" />
            <circle cx="62" cy="97" r="3" fill="#F59E0B" />
            <circle cx="62" cy="115" r="3" fill="#8B5CF6" />
        </svg>
    ),
};

export default function EmptyState({ type = 'clients', title, description, actionLabel, onAction }) {
    const svg = illustrations[type] || illustrations.clients;

    return (
        <div className="flex flex-col items-center justify-center py-16 px-8" data-testid={`empty-state-${type}`}>
            <div className="w-48 h-36 mb-6 opacity-90">
                {svg}
            </div>
            <h3 className="text-lg font-semibold text-[#1E293B] mb-2">{title}</h3>
            {description && (
                <p className="text-sm text-slate-500 text-center max-w-sm mb-6">{description}</p>
            )}
            {actionLabel && onAction && (
                <Button
                    data-testid={`empty-state-action-${type}`}
                    onClick={onAction}
                    className="bg-[#0055FF] hover:bg-[#0044CC] text-white h-11 px-6 text-sm font-medium transition-all hover:scale-105 hover:shadow-lg hover:shadow-blue-200"
                >
                    <Plus className="h-4 w-4 mr-2" />
                    {actionLabel}
                </Button>
            )}
        </div>
    );
}
