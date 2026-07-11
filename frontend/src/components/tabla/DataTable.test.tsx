/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DataTable } from './DataTable';

describe('DataTable', () => {
  const columns = [
    { accessorKey: 'id', header: 'ID' },
    { accessorKey: 'name', header: 'Name' },
  ];

  const data = Array.from({ length: 30 }).map((_, i) => ({ id: i + 1, name: `Item ${i + 1}` }));

  it('renderiza en modo cliente y pagina correctamente si no se pasan props manuales', () => {
    render(<DataTable columns={columns} data={data} />);
    
    // Debería mostrar la primera página (1 a 10 elementos por defecto, tanstack-table usa 10 por default)
    expect(screen.getByText('Item 1')).toBeDefined();
    expect(screen.queryByText('Item 11')).toBeNull();

    // Comprobar la información de paginación
    expect(screen.getByText(/Página 1 de 3/)).toBeDefined();

    // Navegar a la página 2
    const nextButton = screen.getByRole('button', { name: /Siguiente/i });
    fireEvent.click(nextButton);

    expect(screen.getAllByText('Item 11')[0]).toBeDefined();
    expect(screen.getByText(/Página 2 de 3/)).toBeDefined();
  });

  it('renderiza en modo manual (servidor) cuando se le pasa pageCount y pagination', () => {
    const onPaginationChange = vi.fn();
    
    render(
      <DataTable 
        columns={columns} 
        // Solo pasamos los datos de la página actual simulando server-side
        data={data.slice(0, 10)} 
        pageCount={5}
        pagination={{ pageIndex: 0, pageSize: 10 }}
        onPaginationChange={onPaginationChange}
      />
    );
    
    // Muestra los elementos
    expect(screen.getAllByText('Item 1')[0]).toBeDefined();

    // Comprueba paginación delegada
    expect(screen.getByText(/Página 1 de 5/)).toBeDefined();

    // Navegar a la página 2 dispara el callback en vez de paginar internamente
    const nextButton = screen.getByRole('button', { name: /Siguiente/i });
    fireEvent.click(nextButton);

    expect(onPaginationChange).toHaveBeenCalled();
  });
});
