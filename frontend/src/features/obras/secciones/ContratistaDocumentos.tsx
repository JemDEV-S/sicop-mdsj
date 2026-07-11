import type { ObraDetalleResponse } from '../types';

export function Contratista({ obra }: { obra: ObraDetalleResponse }) {
  // TODO T-XX: backend aún no expone datos de contratista (ver AC-02.3)
  // habilitar cuando ObraDetalleResponse incluya ruc/razon_social/monto_contratado
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _ = obra; 
  return null;
}

export function Documentos({ obra }: { obra: ObraDetalleResponse }) {
  // TODO T-XX: backend aún no expone enlaces de descarga de documentos (ver AC-02.4)
  // habilitar cuando ObraDetalleResponse incluya array de documentos_descarga
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _ = obra;
  return null;
}
