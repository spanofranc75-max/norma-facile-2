/**
 * TabBar — Horizontal tab strip for multi-tab navigation.
 * Sits below navbar, 36px height. Styled with Tailwind.
 */
import { X, Plus } from 'lucide-react';
import { useTabContext } from '../contexts/TabContext';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';

export default function TabBar() {
    const { tabs, activeTabId, switchTab, closeTab, openTab } = useTabContext();

    if (tabs.length <= 1) return null; // hide when single tab

    const isFull = tabs.length >= 4;

    return (
        <div
            className="flex items-center h-9 bg-slate-100 border-b border-slate-200 px-2 gap-0.5 overflow-x-auto"
            data-testid="tab-bar"
        >
            {tabs.map(tab => {
                const isActive = tab.id === activeTabId;
                return (
                    <button
                        key={tab.id}
                        data-testid={`tab-${tab.id}`}
                        onClick={() => switchTab(tab.id)}
                        className={`group relative flex items-center gap-1.5 px-3 h-full text-xs whitespace-nowrap transition-colors
                            ${isActive
                                ? 'bg-white border-t-2 border-t-[#0055FF] text-slate-900 font-medium shadow-sm'
                                : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700 border-t-2 border-t-transparent'
                            }`}
                    >
                        {/* Dirty indicator */}
                        {tab.isDirty && (
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0" data-testid={`tab-dirty-${tab.id}`} />
                        )}

                        {/* Title */}
                        <span className="max-w-[120px] truncate">
                            {tab.title?.length > 20 ? tab.title.slice(0, 20) + '...' : tab.title}
                        </span>

                        {/* Close button (only if more than 1 tab) */}
                        {tabs.length > 1 && (
                            <span
                                data-testid={`tab-close-${tab.id}`}
                                onClick={(e) => { e.stopPropagation(); closeTab(tab.id); }}
                                className="ml-1 p-0.5 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-700 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                <X className="h-3 w-3" />
                            </span>
                        )}
                    </button>
                );
            })}

            {/* New tab button */}
            <TooltipProvider>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <button
                            data-testid="tab-new-btn"
                            disabled={isFull}
                            onClick={() => openTab('/dashboard', 'Dashboard')}
                            className={`flex items-center justify-center h-6 w-6 ml-1 rounded transition-colors
                                ${isFull
                                    ? 'text-slate-300 cursor-not-allowed'
                                    : 'text-slate-400 hover:bg-slate-200 hover:text-slate-700'
                                }`}
                        >
                            <Plus className="h-3.5 w-3.5" />
                        </button>
                    </TooltipTrigger>
                    {isFull && (
                        <TooltipContent>
                            <p>Chiudi una tab per aprirne un'altra</p>
                        </TooltipContent>
                    )}
                </Tooltip>
            </TooltipProvider>
        </div>
    );
}
