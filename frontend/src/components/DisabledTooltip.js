/**
 * DisabledTooltip — Wraps a disabled button with a tooltip explanation.
 * Radix tooltips don't fire on disabled elements, so we wrap in a span.
 */
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from './ui/tooltip';

export function DisabledTooltip({ children, reason, show = true }) {
    if (!show || !reason) return children;
    return (
        <TooltipProvider delayDuration={200}>
            <Tooltip>
                <TooltipTrigger asChild>
                    <span className="inline-block" tabIndex={0}>{children}</span>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="bg-[#1E293B] text-white max-w-[220px]">
                    <p>{reason}</p>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}
