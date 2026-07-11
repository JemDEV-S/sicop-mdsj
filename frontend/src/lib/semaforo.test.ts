import { describe, it, expect } from 'vitest';
import { calcularSemaforo } from './semaforo';

describe('calcularSemaforo', () => {
  describe('direccion: mayor es mejor', () => {
    const v = 80;
    const a = 50;

    it('devuelve ok cuando el valor es estrictamente mayor al umbral verde', () => {
      expect(calcularSemaforo(81, v, a, 'mayor')).toBe('ok');
    });

    it('devuelve ok cuando el valor es EXACTAMENTE IGUAL al umbral verde (caso límite)', () => {
      expect(calcularSemaforo(80, v, a, 'mayor')).toBe('ok');
    });

    it('devuelve alerta cuando el valor es estrictamente mayor al amarillo y menor al verde', () => {
      expect(calcularSemaforo(79, v, a, 'mayor')).toBe('alerta');
    });

    it('devuelve alerta cuando el valor es EXACTAMENTE IGUAL al umbral amarillo (caso límite)', () => {
      expect(calcularSemaforo(50, v, a, 'mayor')).toBe('alerta');
    });

    it('devuelve critico cuando el valor es estrictamente menor al amarillo', () => {
      expect(calcularSemaforo(49, v, a, 'mayor')).toBe('critico');
    });
  });

  describe('direccion: menor es mejor', () => {
    const v = 5;
    const a = 15;

    it('devuelve ok cuando el valor es estrictamente menor al umbral verde', () => {
      expect(calcularSemaforo(4, v, a, 'menor')).toBe('ok');
    });

    it('devuelve ok cuando el valor es EXACTAMENTE IGUAL al umbral verde (caso límite)', () => {
      expect(calcularSemaforo(5, v, a, 'menor')).toBe('ok');
    });

    it('devuelve alerta cuando el valor es estrictamente menor al amarillo y mayor al verde', () => {
      expect(calcularSemaforo(14, v, a, 'menor')).toBe('alerta');
    });

    it('devuelve alerta cuando el valor es EXACTAMENTE IGUAL al umbral amarillo (caso límite)', () => {
      expect(calcularSemaforo(15, v, a, 'menor')).toBe('alerta');
    });

    it('devuelve critico cuando el valor es estrictamente mayor al amarillo', () => {
      expect(calcularSemaforo(16, v, a, 'menor')).toBe('critico');
    });
  });
});
