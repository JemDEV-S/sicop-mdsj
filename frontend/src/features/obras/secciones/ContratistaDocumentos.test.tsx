/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { Contratista, Documentos } from './ContratistaDocumentos';
import type { ObraDetalleResponse } from '../types';

describe('Renderizado Condicional (Ocultamiento Estricto)', () => {
  it('Contratista debe retornar null y no dejar rastros en el DOM si los datos no están (AC-02.3)', () => {
    // Objeto mock que respeta el tipo (que por T-39 NO tiene campos de contratista)
    const mockObra = {} as ObraDetalleResponse;
    const { container } = render(<Contratista obra={mockObra} />);
    
    // Verificamos que el contenedor esté completamente vacío
    expect(container.innerHTML).toBe('');
  });

  it('Documentos debe retornar null y no dejar rastros en el DOM si los datos no están (AC-02.4)', () => {
    // Objeto mock que respeta el tipo (que por T-39 NO tiene array de documentos)
    const mockObra = {} as ObraDetalleResponse;
    const { container } = render(<Documentos obra={mockObra} />);
    
    // Verificamos que el contenedor esté completamente vacío
    expect(container.innerHTML).toBe('');
  });
});
