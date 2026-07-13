import type { ObraDetalleResponse } from '../types';

export function Cronograma({ obra }: { obra: ObraDetalleResponse }) {
  return (
    <div className="bg-white border border-gray-200 shadow-sm p-4 rounded-sm h-full">
      <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">Cronograma</h3>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Viabilidad</span>
          <span className="font-medium text-gray-900">{obra.fecha_viabilidad || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Inicio de Ejecución</span>
          <span className="font-medium text-gray-900">{obra.fec_ini_ejecucion || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Fin de Ejecución</span>
          <span className="font-medium text-gray-900">{obra.fec_fin_ejecucion || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Último Devengado</span>
          <span className="font-medium text-gray-900">{obra.ultimo_devengado || '-'}</span>
        </div>
      </div>
    </div>
  );
}
