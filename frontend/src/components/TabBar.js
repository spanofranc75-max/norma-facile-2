import { useLocation } from 'react-router-dom';
import { useTabContext } from '../contexts/TabContext';
import { X } from 'lucide-react';
import { useEffect } from 'react';

export default function TabBar() {
    const { tabs, closeTab, switchTab, ensureTab } = useTabContext();
    const location = useLocation();
    const currentPath = location.pathname;

    // Auto-register current page as a tab
    useEffect(() => {
        if (currentPath && currentPath !== '/') {
            ensureTab(currentPath);
        }
    }, [currentPath, ensureTab]);

    if (tabs.length === 0) return null;

    return (
        <div
            className="bg-white border-b border-slate-200 flex items-center gap-0 overflow-x-auto scrollbar-thin"
            data-testid="tab-bar"
            style={{ minHeight: 36 }}
        >
            {tabs.map((tab) => {
                const isActive = currentPath === tab.path;
                const Icon = tab.icon;
                return (
                    <div
                        key={tab.path}
                        data-testid={`tab-${tab.path.replace(/\//g, '-')}`}
                        className={`
                            group flex items-center gap-1.5 px-3 py-1.5 cursor-pointer
                            border-r border-slate-100 shrink-0 max-w-[200px] transition-colors
                            ${isActive
                                ? 'bg-blue-50 border-b-2 border-b-blue-600 text-blue-700'
                                : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700 border-b-2 border-b-transparent'
                            }
                        `}
                        onClick={() => switchTab(tab.path)}
                    >
                        {Icon && <Icon className="w-3.5 h-3.5 shrink-0" />}
                        <span className="text-[11px] font-medium truncate leading-none">
                            {tab.label}
                        </span>
                        <button
                            data-testid={`tab-close-${tab.path.replace(/\//g, '-')}`}
                            className="ml-0.5 p-0.5 rounded hover:bg-slate-200 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                            onClick={(e) => {
                                e.stopPropagation();
                                closeTab(tab.path);
                            }}
                        >
                            <X className="w-3 h-3" />
                        </button>
                    </div>
                );
            })}
        </div>
    );
}
