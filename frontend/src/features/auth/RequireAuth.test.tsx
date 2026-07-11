import '@testing-library/jest-dom/vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, afterEach } from 'vitest';
import RequireAuth from './RequireAuth';
import * as useAuthModule from './hooks/useAuth';

// Test component para verificar transiciones
const ProtectedComponent = () => <div data-testid="protected-content">Contenido Protegido</div>;
const LoginComponent = () => <div data-testid="login-content">Login</div>;

describe('RequireAuth Guard', () => {
  afterEach(() => {
    vi.clearAllMocks();
    cleanup();
  });
  const renderWithRouter = () => {
    return render(
      <MemoryRouter initialEntries={['/interno']}>
        <Routes>
          <Route path="/login" element={<LoginComponent />} />
          <Route path="/interno" element={<RequireAuth />}>
            <Route index element={<ProtectedComponent />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
  };

  it('debe mostrar "Cargando..." cuando isLoading es true y NO redirigir a /login prematuramente', () => {
    vi.spyOn(useAuthModule, 'useAuth').mockReturnValue({
      isLoading: true,
      isAuthenticated: false
    });

    renderWithRouter();

    // 1. Mostrar Cargando...
    expect(screen.getByText('Cargando...')).toBeInTheDocument();
    
    // 2. NO renderiza ni el contenido protegido ni el login
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.queryByTestId('login-content')).not.toBeInTheDocument();
  });

  it('debe redirigir a /login cuando isLoading es false y isAuthenticated es false', () => {
    vi.spyOn(useAuthModule, 'useAuth').mockReturnValue({
      isLoading: false,
      isAuthenticated: false
    });

    renderWithRouter();

    // Redirigido exitosamente a /login
    expect(screen.getByTestId('login-content')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('debe renderizar el contenido protegido cuando isLoading es false y isAuthenticated es true', () => {
    vi.spyOn(useAuthModule, 'useAuth').mockReturnValue({
      isLoading: false,
      isAuthenticated: true
    });

    renderWithRouter();

    // Renderiza el contenido interno, no hay redirección
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    expect(screen.queryByTestId('login-content')).not.toBeInTheDocument();
  });
});
