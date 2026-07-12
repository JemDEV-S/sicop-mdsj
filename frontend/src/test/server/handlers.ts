import { http, HttpResponse } from 'msw';
import type { ProveedoresListado, ProveedorPublicoItem } from '../../features/proveedores/types';

// Mock de contrato Pydantic confirmado en T-43, ver bitácora — pendiente de verificación E2E real hasta .bak de SIGA
const mockProveedores: ProveedorPublicoItem[] = [
  {
    ruc: '20123456789',
    nombre: 'CONSTRUCTORA LOS ANDES S.A.C.',
    tipo_persona: 'JURIDICA',
    giro: 'CONSTRUCCION DE EDIFICIOS',
    flag_mype: 'S',
    flag_rnp: 'S',
    flag_consorcio: 'N',
    monto_acumulado: 150000.5,
    nro_ordenes: 3,
  },
  {
    ruc: '10987654321',
    nombre: 'JUAN PEREZ CONSULTING',
    tipo_persona: 'NATURAL',
    giro: 'SERVICIOS PROFESIONALES',
    flag_mype: 'N',
    flag_rnp: 'S',
    flag_consorcio: 'N',
    monto_acumulado: 45000,
    nro_ordenes: 1,
  },
];

export const handlers = [
  http.get(new RegExp('.*/api/v1/publico/proveedores'), ({ request }) => {
    const url = new URL(request.url);
    const q = url.searchParams.get('q');
    
    let filtered = [...mockProveedores];
    if (q) {
      filtered = filtered.filter(p => 
        p.ruc?.includes(q) || p.nombre?.toLowerCase().includes(q.toLowerCase())
      );
    }
    
    const response: ProveedoresListado = {
      items: filtered,
      total: filtered.length,
      page: 1,
      size: 25,
    };

    return HttpResponse.json(response);
  }),
];
