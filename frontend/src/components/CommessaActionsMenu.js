/**
 * CommessaActionsMenu — Grouped action buttons in a dropdown menu.
 * Replaces the 12+ inline buttons with a clean, organized menu.
 */
import { useState } from 'react';
import { Button } from '../components/ui/button';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel,
} from '../components/ui/dropdown-menu';
import {
    Download, FileText, Award, Loader2, ChevronDown, ClipboardList,
} from 'lucide-react';

export default function CommessaActionsMenu({
    commessaId, commessaNumero, normativaTipo,
    onDownloadDossier, onDownloadPacco, onDownloadTemplate111,
    onDopAutomatica, onEtichettaCE, onRintracciabilita,
    onCamDichiarazione, onPaccoRina, onDownloadFoglioLavoro,
    generatingDopAuto,
}) {
    const isEN1090 = normativaTipo === 'EN_1090';

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button size="sm" className="bg-[#0055FF] text-white hover:bg-[#0044CC] text-xs" data-testid="btn-genera-documenti">
                    <Download className="h-3.5 w-3.5 mr-1.5" />
                    Genera Documenti
                    <ChevronDown className="h-3 w-3 ml-1" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="text-[10px] text-slate-400 uppercase">Documenti Base</DropdownMenuLabel>
                <DropdownMenuItem onClick={onDownloadDossier} data-testid="menu-dossier" className="text-xs cursor-pointer">
                    <Download className="h-3.5 w-3.5 mr-2 text-blue-600" /> Dossier PDF
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onDownloadPacco} data-testid="menu-pacco" className="text-xs cursor-pointer">
                    <FileText className="h-3.5 w-3.5 mr-2 text-emerald-600" /> Pacco Documenti
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onDownloadTemplate111} data-testid="menu-template-111" className="text-xs cursor-pointer">
                    <Award className="h-3.5 w-3.5 mr-2 text-amber-600" /> Template 111
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="text-[10px] text-slate-400 uppercase">Officina</DropdownMenuLabel>
                <DropdownMenuItem onClick={onDownloadFoglioLavoro} data-testid="menu-foglio-lavoro" className="text-xs cursor-pointer">
                    <ClipboardList className="h-3.5 w-3.5 mr-2 text-orange-600" /> Foglio Lavoro (Stampa)
                </DropdownMenuItem>
                {isEN1090 && (
                    <>
                        <DropdownMenuSeparator />
                        <DropdownMenuLabel className="text-[10px] text-slate-400 uppercase">EN 1090</DropdownMenuLabel>
                        <DropdownMenuItem onClick={onDopAutomatica} disabled={generatingDopAuto} data-testid="menu-dop-auto" className="text-xs cursor-pointer">
                            {generatingDopAuto ? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" /> : <FileText className="h-3.5 w-3.5 mr-2 text-indigo-600" />}
                            DoP Automatica
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={onEtichettaCE} data-testid="menu-etichetta-ce" className="text-xs cursor-pointer">
                            <Award className="h-3.5 w-3.5 mr-2 text-slate-700" /> Etichetta CE
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={onRintracciabilita} data-testid="menu-rintracciabilita" className="text-xs cursor-pointer">
                            <FileText className="h-3.5 w-3.5 mr-2 text-teal-600" /> Rintracciabilita
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={onCamDichiarazione} data-testid="menu-cam" className="text-xs cursor-pointer">
                            <FileText className="h-3.5 w-3.5 mr-2 text-amber-700" /> CAM PNRR
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={onPaccoRina} data-testid="menu-pacco-rina" className="text-xs cursor-pointer">
                            <Download className="h-3.5 w-3.5 mr-2 text-red-700" /> Pacco RINA (ZIP)
                        </DropdownMenuItem>
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
