import type { ObraDetalleResponse } from '../types';

export function Identificacion({ obra }: { obra: ObraDetalleResponse }) {
  return (
    <div className="bg-white border border-gray-200 shadow-sm p-4 rounded-sm space-y-4">
      <div>
        <h2 className="text-xl font-bold text-gray-900">{obra.nombre_inversion || 'Sin nombre de proyecto'}</h2>
        <p className="text-gray-500 text-sm mt-1">Código único: <span className="font-mono text-gray-900">{obra.codigo_unico}</span></p>
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-500">Función</p>
          <p className="font-medium text-gray-900">{obra.funcion || '-'}</p>
        </div>
        <div>
          <p className="text-gray-500">Modalidad</p>
          <p className="font-medium text-gray-900">{obra.modalidad || '-'}</p>
        </div>
        <div>
          <p className="text-gray-500">Estado</p>
          <p className="font-medium text-gray-900">{obra.estado || '-'}</p>
        </div>
        <div>
          <p className="text-gray-500">Tipología</p>
          <p className="font-medium text-gray-900">{obra.tipologia || '-'}</p>
        </div>
      </div>
    </div>
  );
}
