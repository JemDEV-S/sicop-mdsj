import { describe, it, test, expect } from 'vitest';
import { parseMonto, calcularPorcentaje, formatearMoneda, formatPorcentaje, formatFecha } from './formatters';

describe('formatters', () => {
  describe('parseMonto', () => {
    test('convierte string decimal a number correctamente', () => {
      expect(parseMonto('123456.78')).toBe(123456.78);
      expect(parseMonto('-50.25')).toBe(-50.25);
    });

    test('devuelve null para valores falsy o inválidos', () => {
      expect(parseMonto(null)).toBeNull();
      expect(parseMonto(undefined)).toBeNull();
      expect(parseMonto('')).toBeNull();
      expect(parseMonto('abc')).toBeNull();
      expect(parseMonto(NaN)).toBeNull();
    });

    test('preserva el number si ya viene parseado', () => {
      expect(parseMonto(100.5)).toBe(100.5);
      expect(parseMonto(0)).toBe(0);
    });
  });

  describe('calcularPorcentaje', () => {
    test('calcula el porcentaje y lo redondea a 2 decimales', () => {
      expect(calcularPorcentaje('25', '100')).toBe(25);
      expect(calcularPorcentaje('1', '3')).toBe(33.33);
      expect(calcularPorcentaje('2', '3')).toBe(66.67);
      expect(calcularPorcentaje(10, 200)).toBe(5);
    });

    test('devuelve null si el total es 0 o inválido, para evitar Infinity o NaN', () => {
      expect(calcularPorcentaje('50', '0')).toBeNull();
      expect(calcularPorcentaje('50', '')).toBeNull();
      expect(calcularPorcentaje('50', null)).toBeNull();
    });

    test('devuelve null si la parte es inválida', () => {
      expect(calcularPorcentaje(null, '100')).toBeNull();
      expect(calcularPorcentaje('abc', '100')).toBeNull();
    });

    test('devuelve 0 legítimo si la parte es 0', () => {
      expect(calcularPorcentaje('0', '100')).toBe(0);
      expect(calcularPorcentaje(0, 100)).toBe(0);
    });
  });

  describe('formatearMoneda', () => {
    test('formatea correctamente números válidos', () => {
      expect(formatearMoneda(1500.5).replace(/\s/g, ' ')).toContain('1,500.50');
      expect(formatearMoneda(0).replace(/\s/g, ' ')).toContain('0.00');
    });

    test('soporta formato compacto', () => {
      expect(formatearMoneda(1500000, true).replace(/\s/g, ' ')).toContain('1.5M');
      expect(formatearMoneda(1500, true).replace(/\s/g, ' ')).toContain('1.5K');
    });

    test('devuelve ND cuando el valor es null (dato faltante o parse fallido)', () => {
      // Direct null
      expect(formatearMoneda(null)).toBe('ND');
      // Simulated full pipeline from undefined/NaN
      expect(formatearMoneda(parseMonto(undefined))).toBe('ND');
      expect(formatearMoneda(parseMonto(NaN))).toBe('ND');
      expect(formatearMoneda(parseMonto(''))).toBe('ND');
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
