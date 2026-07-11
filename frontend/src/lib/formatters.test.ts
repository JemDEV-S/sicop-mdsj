import { describe, it, expect } from 'vitest';
import { formatSoles, formatPorcentaje, formatFecha } from './formatters';

describe('formatters', () => {
  describe('formatSoles', () => {
    it('formatea números a S/ correctamente', () => {
      // Nota: Intl usa espacio insecable o normal dependiendo del runtime, simplificamos con replace
      expect(formatSoles(1500.5).replace(/\s/g, ' ')).toContain('1,500.50');
      expect(formatSoles(1500.5).replace(/\s/g, ' ')).toContain('S/');
    });

    it('maneja nulos y undefined', () => {
      expect(formatSoles(null)).toBe('S/ 0.00');
      expect(formatSoles(undefined)).toBe('S/ 0.00');
    });
  });

  describe('formatPorcentaje', () => {
    it('formatea números enteros a porcentaje', () => {
      // El input es el porcentaje real (ej 95 para 95%)
      expect(formatPorcentaje(95).replace(/\s/g, ' ')).toContain('95.0%');
    });

    it('respeta los decimales indicados', () => {
      expect(formatPorcentaje(95.45, 2).replace(/\s/g, ' ')).toContain('95.45%');
      expect(formatPorcentaje(95.45, 0).replace(/\s/g, ' ')).toContain('95%');
    });

    it('maneja nulos', () => {
      expect(formatPorcentaje(null)).toBe('0%');
    });
  });

  describe('formatFecha', () => {
    it('formatea un string ISO a DD/MM/YYYY', () => {
      expect(formatFecha('2026-07-11T12:00:00Z')).toBe('11/07/2026');
    });

    it('maneja nulos y strings inválidos', () => {
      expect(formatFecha(null)).toBe('-');
      expect(formatFecha('invalid')).toBe('-');
    });
  });
});
