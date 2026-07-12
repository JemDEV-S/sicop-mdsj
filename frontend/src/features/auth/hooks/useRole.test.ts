/**
 * @vitest-environment jsdom
 */
import { renderHook } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useRole } from './useRole';
import { useAuthStore } from '../../../store/auth';

describe('useRole', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
  });

  it('debe retornar undefined si no hay usuario autenticado', () => {
    const { result } = renderHook(() => useRole());
    expect(result.current).toBeUndefined();
  });

  it('debe retornar el rol del usuario (string puro) extraido del shape exacto del Pydantic MeResponse', () => {
    // Reproducción literal del schema Pydantic del backend (MeResponse)
    const mockMeResponse = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      usuario: 'operador_prueba',
      nombre_completo: 'Operador Test',
      email: null,
      rol: 'operativo',
      centros_costo: [],
      debe_cambiar_password: false
    };

    // Inyectamos el usuario simulando una sesión activa
    useAuthStore.setState({
      user: mockMeResponse,
      isAuthenticated: true,
      isLoading: false
    });

    const { result } = renderHook(() => useRole());

    // La regresión reportada evaluaba 'mockMeResponse.rol.codigo', lo cual fallaría aquí.
    // El assert verifica que se extrae correctamente la cadena primitiva.
    expect(result.current).toBe('operativo');
    expect(typeof result.current).toBe('string');
  });
});
