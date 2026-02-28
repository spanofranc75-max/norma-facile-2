/**
 * QualityScoreWidget — Radial progress bar with score breakdown and insights.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Shield, ChevronRight, AlertTriangle, Lightbulb, Info } from 'lucide-react';

const INSIGHT_ICONS = {
    warning: AlertTriangle,
    tip: Lightbulb,
    info: Info,
};

const INSIGHT_COLORS = {
    warning: 'text-amber-600 bg-amber-50',
    tip: 'text-blue-600 bg-blue-50',
    info: 'text-slate-600 bg-slate-50',
};

function RadialProgress({ score, size = 120, strokeWidth = 10 }) {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    const center = size / 2;

    let strokeColor;
    if (score >= 80) strokeColor = '#10B981';
    else if (score >= 50) strokeColor = '#F59E0B';
    else strokeColor = '#EF4444';

    return (
        <div className="relative" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="-rotate-90">
                <circle
                    cx={center} cy={center} r={radius}
                    fill="none" stroke="#E2E8F0" strokeWidth={strokeWidth}
                />
                <circle
                    cx={center} cy={center} r={radius}
                    fill="none" stroke={strokeColor} strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    className="transition-all duration-1000 ease-out"
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-[#1E293B]">{score}</span>
                <span className="text-[9px] text-slate-400 font-medium">/100</span>
            </div>
        </div>
    );
}

function BreakdownBar({ label, score, max }) {
    const pct = max > 0 ? Math.round((score / max) * 100) : 0;
    return (
        <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500 w-[100px] truncate">{label}</span>
            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                    className="h-full rounded-full transition-all duration-700 ease-out"
                    style={{
                        width: `${pct}%`,
                        backgroundColor: pct >= 75 ? '#10B981' : pct >= 40 ? '#F59E0B' : '#EF4444',
                    }}
                />
            </div>
            <span className="text-[10px] font-mono text-slate-400 w-[32px] text-right">{score}/{max}</span>
        </div>
    );
}

export default function QualityScoreWidget() {
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        apiRequest('/dashboard/quality-score')
            .then(setData)
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <Card className="border-gray-200" data-testid="quality-score-widget">
                <CardContent className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0055FF]" />
                </CardContent>
            </Card>
        );
    }

    if (!data) return null;

    const bd = data.breakdown || {};

    return (
        <Card className="border-gray-200 overflow-hidden" data-testid="quality-score-widget">
            <CardHeader className="bg-slate-50 border-b border-gray-200 py-3 px-5">
                <CardTitle className="text-sm font-semibold text-[#1E293B] flex items-center gap-2">
                    <Shield className="h-4 w-4 text-[#0055FF]" /> Officina Quality Score
                </CardTitle>
            </CardHeader>
            <CardContent className="p-5">
                <div className="flex items-start gap-5">
                    {/* Radial */}
                    <div className="flex flex-col items-center gap-1.5">
                        <RadialProgress score={data.total_score} />
                        <Badge
                            data-testid="quality-level"
                            className={`text-[10px] ${
                                data.level_color === 'emerald' ? 'bg-emerald-100 text-emerald-800' :
                                data.level_color === 'blue' ? 'bg-blue-100 text-blue-800' :
                                data.level_color === 'amber' ? 'bg-amber-100 text-amber-800' :
                                'bg-slate-100 text-slate-600'
                            }`}
                        >
                            {data.level}
                        </Badge>
                    </div>

                    {/* Breakdown */}
                    <div className="flex-1 space-y-2 pt-1">
                        {Object.values(bd).map(b => (
                            <BreakdownBar key={b.label} label={b.label} score={b.score} max={b.max} />
                        ))}
                    </div>
                </div>

                {/* Insights */}
                {data.insights && data.insights.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
                        {data.insights.map((insight, i) => {
                            const IIcon = INSIGHT_ICONS[insight.type] || Info;
                            const iColor = INSIGHT_COLORS[insight.type] || INSIGHT_COLORS.info;
                            return (
                                <button
                                    key={i}
                                    data-testid={`insight-${i}`}
                                    onClick={() => insight.action && navigate(insight.action)}
                                    className={`flex items-start gap-2.5 w-full text-left p-2.5 rounded-lg ${iColor} hover:opacity-80 transition-opacity`}
                                >
                                    <IIcon className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs leading-relaxed">{insight.text}</p>
                                        {insight.points > 0 && (
                                            <p className="text-[10px] font-semibold mt-0.5 opacity-70">+{insight.points} punti</p>
                                        )}
                                    </div>
                                    <ChevronRight className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 opacity-50" />
                                </button>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
