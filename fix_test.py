import re

with open('frontend/src/components/tabla/DataTable.test.tsx', 'a') as f:
    f.write("""
  it('renderiza el estado de carga (Cargando...) cuando isLoading es true', () => {
    render(<DataTable columns={columns} data={[]} isLoading={true} />);
    expect(screen.getByText('Cargando...')).toBeDefined();
  });
""")

