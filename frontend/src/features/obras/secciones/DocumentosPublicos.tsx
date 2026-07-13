import { FileText, Download, FileArchive } from 'lucide-react';
import { useDocumentosObra } from '../media/hooks';
import { urlDescargaMedia } from '../media/api';
import type { DocumentoPublicoItem } from '../media/types';
import { formatFecha } from '@/lib/formatters';

const tipoLabel: Record<string, string> = {
  expediente_tecnico: 'Expediente técnico',
  contrato: 'Contrato',
  f8: 'Formato 8',
  f9: 'Formato 9',
  otro: 'Documento',
};

function etiquetaTipo(tipo: string): string {
  return tipoLabel[tipo] ?? tipo;
}

function formatoTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DocumentosPublicosProps {
  codigoUnico: string;
}

export function DocumentosPublicos({ codigoUnico }: DocumentosPublicosProps) {
  const { data: documentos, isLoading, isError } = useDocumentosObra(codigoUnico);

  return (
    <div className="rounded-2xl bg-card border border-border overflow-hidden">
      <header className="flex items-center gap-2 px-6 py-4 border-b border-border bg-muted/40">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <FileText className="w-4 h-4" aria-hidden="true" />
        </span>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-foreground">Documentos disponibles</h3>
          <p className="text-xs text-muted-foreground">
            Expedientes, contratos y formatos publicados
          </p>
        </div>
        {documentos && documentos.length > 0 ? (
          <span className="text-xs font-medium text-muted-foreground tabular-nums">
            {documentos.length} {documentos.length === 1 ? 'documento' : 'documentos'}
          </span>
        ) : null}
      </header>

      <div className="p-6">
        {isLoading ? (
          <ul className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <li key={i} className="h-14 bg-muted animate-pulse rounded-lg" aria-hidden="true" />
            ))}
          </ul>
        ) : isError || !documentos || documentos.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-muted/30 p-8 text-center">
            <FileArchive
              className="w-7 h-7 text-muted-foreground mx-auto mb-3"
              aria-hidden="true"
            />
            <p className="text-sm font-medium text-foreground">
              {isError
                ? 'No se pudieron cargar los documentos'
                : 'Aún no hay documentos publicados'}
            </p>
            <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
              {isError
                ? 'Intenta recargar la página en unos minutos.'
                : 'Cuando la municipalidad publique el expediente técnico, contrato u otros formatos, podrás descargarlos aquí.'}
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {documentos.map((doc) => (
              <DocumentoFila key={doc.id} doc={doc} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function DocumentoFila({ doc }: { doc: DocumentoPublicoItem }) {
  return (
    <li>
      <a
        href={urlDescargaMedia(doc.ruta_relativa)}
        target="_blank"
        rel="noopener noreferrer"
        download={doc.nombre_original}
        className="group flex items-center gap-4 p-3 rounded-lg border border-border bg-card hover:border-primary hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors"
      >
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
          <FileText className="w-5 h-5" aria-hidden="true" />
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground truncate">
            {etiquetaTipo(doc.tipo)}
          </p>
          <p className="text-xs text-muted-foreground truncate" title={doc.nombre_original}>
            {doc.nombre_original} · {formatoTamano(doc.tamano_bytes)} · {formatFecha(doc.subido_en)}
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary shrink-0 group-hover:gap-2 transition-all">
          <Download className="w-4 h-4" aria-hidden="true" />
          Descargar
        </span>
      </a>
    </li>
  );
}
