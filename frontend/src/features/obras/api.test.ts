import { describe, it, expect } from 'vitest';
import { mapSemaforoApiToEstado } from './api';

describe('mapSemaforoApiToEstado', () => {
  it('resuelve correctamente los tres valores válidos para el frontend', () => {
    expect(mapSemaforoApiToEstado('ok')).toBe('ok');
    expect(mapSemaforoApiToEstado('alerta')).toBe('alerta');
    expect(mapSemaforoApiToEstado('critico')).toBe('critico');
  });

  it('maneja "desconocido" devolviendo null', () => {
    expect(mapSemaforoApiToEstado('desconocido')).toBeNull();
  });

  it('rechaza con null valores no contemplados (programación defensiva)', () => {
    expect(mapSemaforoApiToEstado('OK')).toBeNull(); // case sensitive
    expect(mapSemaforoApiToEstado('basura')).toBeNull();
    expect(mapSemaforoApiToEstado('')).toBeNull();
    expect(mapSemaforoApiToEstado('123')).toBeNull();
  });
});
