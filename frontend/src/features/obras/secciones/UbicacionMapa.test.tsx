/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { UbicacionMapa } from './UbicacionMapa';
import type { ObraDetalleResponse } from '../types';

afterEach(() => {
  cleanup();
});

// Mock simple de la obra para el test
const mockObraBase = {
  codigo_unico: "123456",
  nombre_inversion: "Obra de Test",
} as ObraDetalleResponse;

describe('UbicacionMapa', () => {
  it('renderiza mensaje de fallback cuando las coordenadas son null', () => {
    const obraNull = { ...mockObraBase, latitud: null, longitud: null };
    render(<UbicacionMapa obra={obraNull} />);
    expect(screen.getByText('No hay coordenadas de ubicación registradas para esta obra.')).toBeDefined();
  });

  it('renderiza mensaje de fallback cuando las coordenadas son exactamente (0, 0) - Null Island', () => {
    const obraCero = { ...mockObraBase, latitud: 0, longitud: 0 };
    render(<UbicacionMapa obra={obraCero} />);
    expect(screen.getByText('No hay coordenadas de ubicación registradas para esta obra.')).toBeDefined();
  });
});
