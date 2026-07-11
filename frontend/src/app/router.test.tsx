/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import { router } from './router';

describe('Public Routing Smoke Test', () => {
  it('contiene la ruta índice y las 4 rutas públicas stub (obras, ejecucion, proveedores, mapa)', () => {
    // Buscamos el PublicLayout que tiene path '/' y children
    const publicLayout = router.routes.find(route => 
      route.path === '/' && route.children && route.children.some(child => child.index)
    );
    
    expect(publicLayout).toBeDefined();
    if (!publicLayout || !publicLayout.children) return;

    // Extraer paths disponibles bajo el public layout
    const paths = publicLayout.children.map(child => child.path).filter(Boolean);

    // Verificar explícitamente los 4 stubs exigidos
    expect(paths).toContain('obras');
    expect(paths).toContain('ejecucion');
    expect(paths).toContain('proveedores');
    expect(paths).toContain('mapa');

    // Comprobar que estas rutas tienen un elemento asociado
    ['obras', 'ejecucion', 'proveedores', 'mapa'].forEach(stub => {
      const route = publicLayout.children!.find(r => r.path === stub);
      expect(route).toBeDefined();
      expect(route?.element).toBeDefined();
    });
  });

  it('tiene configurada la ruta índice (/)', () => {
    const publicLayout = router.routes.find(route => 
      route.path === '/' && route.children && route.children.some(child => child.index)
    );
    const indexRoute = publicLayout?.children?.find(r => r.index);
    expect(indexRoute).toBeDefined();
    expect(indexRoute?.element).toBeDefined();
  });
});
