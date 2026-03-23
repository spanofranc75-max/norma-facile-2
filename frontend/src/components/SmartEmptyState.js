/**
 * SmartEmptyState — Intelligent empty state with contextual guidance.
 * Shows: title, description, primary CTA, "what happens next" hint.
 */
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { ArrowRight } from 'lucide-react';

export default function SmartEmptyState({
    icon: Icon,
    iconColor = 'text-[#0055FF]',
    iconBg = 'bg-blue-50',
    title,
    description,
    ctaLabel,
    ctaAction,
    afterHint,
    testId = 'smart-empty-state',
}) {
    return (
        <Card className="border-dashed border-2 border-slate-200 bg-gradient-to-br from-slate-50/80 to-white" data-testid={testId}>
            <CardContent className="flex flex-col items-center text-center py-12 px-6">
                {Icon && (
                    <div className={`w-14 h-14 rounded-2xl ${iconBg} flex items-center justify-center mb-4`}>
                        <Icon className={`h-7 w-7 ${iconColor}`} />
                    </div>
                )}
                <h3 className="text-base font-bold text-slate-800" data-testid={`${testId}-title`}>
                    {title}
                </h3>
                <p className="text-sm text-slate-500 mt-1.5 max-w-md">
                    {description}
                </p>
                {ctaLabel && ctaAction && (
                    <Button
                        onClick={ctaAction}
                        className="mt-5 bg-[#0055FF] text-white hover:bg-[#0044CC] text-sm"
                        data-testid={`${testId}-cta`}
                    >
                        {ctaLabel} <ArrowRight className="h-4 w-4 ml-1.5" />
                    </Button>
                )}
                {afterHint && (
                    <p className="text-xs text-slate-400 mt-4 max-w-sm italic" data-testid={`${testId}-hint`}>
                        {afterHint}
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
