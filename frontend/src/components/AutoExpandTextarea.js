/**
 * AutoExpandTextarea — Textarea che si espande automaticamente con il testo.
 * Perfetto per campi descrizione in tabelle dove il testo può essere lungo.
 */
import { useRef, useEffect } from 'react';
import { cn } from '../lib/utils';

export function AutoExpandTextarea({ value, onChange, placeholder, className, minRows = 1, ...props }) {
    const ref = useRef(null);

    useEffect(() => {
        if (ref.current) {
            ref.current.style.height = 'auto';
            const scrollH = ref.current.scrollHeight;
            const minH = minRows * 24; // ~24px per row
            ref.current.style.height = `${Math.max(scrollH, minH)}px`;
        }
    }, [value, minRows]);

    return (
        <textarea
            ref={ref}
            value={value || ''}
            onChange={onChange}
            placeholder={placeholder}
            rows={minRows}
            className={cn(
                "flex w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background",
                "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                "resize-none overflow-hidden transition-[height] duration-150",
                "min-h-[28px] leading-[1.4]",
                className,
            )}
            {...props}
        />
    );
}
