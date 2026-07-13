import { describe, it, expect } from 'vitest';
import { semaforoToIconClass } from './utils';

describe('semaforoToIconClass', () => {
  it('debería retornar clases correctas para estados conocidos', () => {
    expect(semaforoToIconClass('verde')).toBe('bg-semaforo-ok text-secondary-foreground');
    expect(semaforoToIconClass('amarillo')).toBe('bg-semaforo-alerta text-accent-foreground');
    expect(semaforoToIconClass('rojo')).toBe('bg-semaforo-critico text-destructive-foreground');
  });

  it('debería retornar el estado neutral para "desconocido"', () => {
    expect(semaforoToIconClass('desconocido')).toBe('bg-muted text-muted-foreground');
  });

  it('debería hacer fail-safe a estado neutral si recibe un string inventado', () => {
    expect(semaforoToIconClass('azul_inventado')).toBe('bg-muted text-muted-foreground');
    expect(semaforoToIconClass('cualquier_cosa')).toBe('bg-muted text-muted-foreground');
  });

  it('debería hacer fail-safe a estado neutral si recibe nulos o indefinidos', () => {
    expect(semaforoToIconClass(null)).toBe('bg-muted text-muted-foreground');
    expect(semaforoToIconClass(undefined)).toBe('bg-muted text-muted-foreground');
  });
});
