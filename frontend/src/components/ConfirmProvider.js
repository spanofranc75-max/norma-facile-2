/**
 * ConfirmProvider — Global confirmation dialog that replaces window.confirm().
 * Works in sandboxed iframes where window.confirm() is blocked.
 *
 * Usage:
 *   import { useConfirm } from '../components/ConfirmProvider';
 *   const confirm = useConfirm();
 *   const ok = await confirm('Sei sicuro?');
 *   if (!ok) return;
 */
import { createContext, useContext, useState, useCallback, useRef } from 'react';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from './ui/alert-dialog';

const ConfirmContext = createContext(null);

export function ConfirmProvider({ children }) {
    const [state, setState] = useState({ open: false, message: '', title: '' });
    const resolveRef = useRef(null);

    const confirm = useCallback((message, title) => {
        return new Promise((resolve) => {
            resolveRef.current = resolve;
            setState({ open: true, message: message || 'Sei sicuro?', title: title || 'Conferma' });
        });
    }, []);

    const handleConfirm = () => {
        setState(s => ({ ...s, open: false }));
        resolveRef.current?.(true);
    };

    const handleCancel = () => {
        setState(s => ({ ...s, open: false }));
        resolveRef.current?.(false);
    };

    return (
        <ConfirmContext.Provider value={confirm}>
            {children}
            <AlertDialog open={state.open} onOpenChange={(v) => { if (!v) handleCancel(); }}>
                <AlertDialogContent data-testid="confirm-dialog">
                    <AlertDialogHeader>
                        <AlertDialogTitle>{state.title}</AlertDialogTitle>
                        <AlertDialogDescription className="whitespace-pre-line">{state.message}</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel data-testid="confirm-cancel" onClick={handleCancel}>Annulla</AlertDialogCancel>
                        <AlertDialogAction data-testid="confirm-ok" onClick={handleConfirm}
                            className="bg-[#0055FF] text-white hover:bg-blue-700">
                            Conferma
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </ConfirmContext.Provider>
    );
}

export function useConfirm() {
    const ctx = useContext(ConfirmContext);
    if (!ctx) throw new Error('useConfirm must be used inside ConfirmProvider');
    return ctx;
}
