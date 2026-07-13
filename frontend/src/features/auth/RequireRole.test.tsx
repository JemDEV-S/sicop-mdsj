/**
 * @vitest-environment jsdom
 */
import '@testing-library/jest-dom/vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, afterEach } from 'vitest';
import RequireRole from './RequireRole';
import * as useRoleModule from './hooks/useRole';

// Test component para verificar transiciones
const ProtectedAdminComponent = () => <div data-testid="admin-content">Contenido de Admin</div>;
const FallbackComponent = () => <div data-testid="fallback-content">Fallback Interno</div>;

describe('RequireRole Guard', () => {
  afterEach(() => {
    vi.clearAllMocks();
    cleanup();
  });

  const renderWithRouter = () => {
    return render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/interno" element={<FallbackComponent />} />
          <Route path="/admin" element={<RequireRole role="admin" />}>
            <Route index element={<ProtectedAdminComponent />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
  };

  it('debe denegar el acceso (redirigir a /interno) cuando NO hay rol disponible', () => {
    vi.spyOn(useRoleModule, 'useRole').mockReturnValue(undefined);

    renderWithRouter();

    expect(screen.getByTestId('fallback-content')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  });

  it('debe denegar el acceso (redirigir a /interno) cuando el rol disponible NO COINCIDE con el requerido', () => {
    vi.spyOn(useRoleModule, 'useRole').mockReturnValue('usuario_comun');

    renderWithRouter();

    expect(screen.getByTestId('fallback-content')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  });

  it('debe permitir el acceso (renderizar children) cuando el rol disponible COINCIDE con el requerido', () => {
    vi.spyOn(useRoleModule, 'useRole').mockReturnValue('admin');

    renderWithRouter();

    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
    expect(screen.queryByTestId('fallback-content')).not.toBeInTheDocument();
  });
});
