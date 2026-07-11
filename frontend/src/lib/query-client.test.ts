import { describe, it, expect } from 'vitest';
import { shouldRetryQuery } from './query-client';

describe('queryClient - shouldRetryQuery', () => {
  it('NO debe reintentar si el error es de Axios con status 401', () => {
    const error401 = {
      isAxiosError: true,
      response: { status: 401 }
    };
    
    // Incluso en el primer intento (failureCount = 0), debe abortar
    expect(shouldRetryQuery(0, error401)).toBe(false);
  });

  it('NO debe reintentar si el error es de Axios con status 403', () => {
    const error403 = {
      isAxiosError: true,
      response: { status: 403 }
    };
    
    expect(shouldRetryQuery(0, error403)).toBe(false);
  });

  it('SÍ debe reintentar si el error es de Axios con status 500 y no superó límite', () => {
    const error500 = {
      isAxiosError: true,
      response: { status: 500 }
    };
    
    // Intento 0: sí reintenta
    expect(shouldRetryQuery(0, error500)).toBe(true);
    // Intento 1 (ya hizo un retry): ya no reintenta más
    expect(shouldRetryQuery(1, error500)).toBe(false);
  });

  it('SÍ debe reintentar si es un error generico de red u otro, respetando el límite', () => {
    const errorGenerico = new Error('Network error');
    
    expect(shouldRetryQuery(0, errorGenerico)).toBe(true);
    expect(shouldRetryQuery(1, errorGenerico)).toBe(false);
  });
});
