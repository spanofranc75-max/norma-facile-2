import { Component } from 'react';

export class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        // Known React DOM errors from browser extensions (Grammarly, Google Translate, etc.)
        if (error?.message?.includes('removeChild') ||
            error?.message?.includes('insertBefore') ||
            error?.message?.includes('appendChild')) {
            console.warn('[ErrorBoundary] DOM manipulation error caught (likely browser extension):', error.message);
            return { hasError: false };
        }
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        if (error?.message?.includes('removeChild') ||
            error?.message?.includes('insertBefore') ||
            error?.message?.includes('appendChild')) {
            return; // Silently ignore DOM manipulation errors
        }
        console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-slate-50">
                    <div className="text-center p-8 max-w-md">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
                            <span className="text-2xl text-red-600">!</span>
                        </div>
                        <h2 className="text-xl font-bold text-slate-900 mb-2">Si è verificato un errore</h2>
                        <p className="text-sm text-slate-600 mb-4">
                            Qualcosa è andato storto. Prova a ricaricare la pagina.
                        </p>
                        <button
                            onClick={() => {
                                this.setState({ hasError: false, error: null });
                                window.location.reload();
                            }}
                            className="px-6 py-2 bg-[#0055FF] text-white rounded-lg hover:bg-[#0044CC] transition-colors"
                        >
                            Ricarica pagina
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
