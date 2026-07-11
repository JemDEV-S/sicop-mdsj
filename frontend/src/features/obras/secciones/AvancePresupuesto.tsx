import type { ObraDetalleResponse } from '../types';
import { formatSoles } from '../../../lib/formatters';
import Semaforo from '../../../components/Semaforo';
import { mapSemaforoApiToEstado } from '../api';

export function AvancePresupuesto({ obra }: { obra: ObraDetalleResponse }) {
  const estado = mapSemaforoApiToEstado(obra.semaforo);
  const fisico = obra.avance_fisico;
  const textoFisico = fisico !== null && fisico !== undefined ? `${fisico.toFixed(1)}%` : 'Desconocido';

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="bg-white border border-gray-200 shadow-sm p-4 rounded-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">Avance</h3>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 text-sm">Físico</span>
            {estado ? <Semaforo estado={estado} texto={textoFisico} /> : <span className="text-sm font-medium text-gray-900">{textoFisico}</span>}
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-600 text-sm">Financiero</span>
            <span className="text-sm font-medium text-gray-900">
              {obra.montos_ejecucion.porcentaje_devengado !== null && obra.montos_ejecucion.porcentaje_devengado !== undefined 
                ? `${obra.montos_ejecucion.porcentaje_devengado.toFixed(1)}%` 
                : '0%'}
            </span>
          </div>
          <div className="pt-2 border-t border-gray-100 flex justify-between">
            <span className="text-gray-600 text-sm">Etapa</span>
            <span className="text-sm font-medium text-gray-900">{obra.etapa_f8 || '-'}</span>
          </div>
        </div>
      </div>
      <div className="bg-white border border-gray-200 shadow-sm p-4 rounded-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">Presupuesto</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">PIA</span>
            <span className="font-medium text-gray-900">{formatSoles(obra.montos_ejecucion.pia)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">PIM</span>
            <span className="font-medium text-gray-900">{formatSoles(obra.montos_ejecucion.pim)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Certificado</span>
            <span className="font-medium text-gray-900">{formatSoles(obra.montos_ejecucion.certificado)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Devengado</span>
            <span className="font-medium text-gray-900">{formatSoles(obra.montos_ejecucion.devengado)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
