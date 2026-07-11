import type { ColumnDef } from '@tanstack/react-table';
import Semaforo from '../../components/Semaforo';
import { DataTable } from '../../components/tabla/DataTable';
import WrapperGrafico from '../../components/grafico/WrapperGrafico';
import WrapperMapa from '../../components/mapa/WrapperMapa';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { Marker, Popup } from 'react-leaflet';

export default function Sandbox() {
  const data = [
    { id: 1, obra: 'Colegio A', avance: 95 },
    { id: 2, obra: 'Veredas B', avance: 60 },
    { id: 3, obra: 'Parque C', avance: 20 },
  ];

  const columns: ColumnDef<any>[] = [
    { accessorKey: 'id', header: 'ID' },
    { accessorKey: 'obra', header: 'Obra' },
    { accessorKey: 'avance', header: 'Avance (%)' },
  ];

  const chartData = [
    { name: 'Ene', value: 400 },
    { name: 'Feb', value: 300 },
    { name: 'Mar', value: 500 },
  ];

  return (
    <div className="p-8 space-y-12 bg-gray-50 min-h-screen">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Sandbox de Componentes (T-36)</h1>
        <p className="text-gray-600">Entorno protegido para validar el design system institucional.</p>
      </div>

      <section>
        <h2 className="text-xl font-semibold mb-4 text-primary">1. Semáforos</h2>
        <div className="flex gap-4">
          {/* Valores de ejemplo — los umbrales reales vienen de sistema.umbrales_semaforos vía API (ver T-17 y T-55) */}
          <Semaforo estado="ok" texto="Ok (>= 80%)" />
          <Semaforo estado="alerta" texto="Alerta (50-79%)" />
          <Semaforo estado="critico" texto="Crítico (< 50%)" />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4 text-primary">2. DataTable</h2>
        <DataTable columns={columns} data={data} />
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4 text-primary">3. Wrapper Gráfico (Recharts)</h2>
        <WrapperGrafico>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="name" axisLine={false} tickLine={false} />
            <YAxis axisLine={false} tickLine={false} />
            <Tooltip 
              cursor={{ fill: '#F3F4F6' }} 
              contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E5E7EB' }} 
            />
            <Legend />
            {/* Color inyectado desde CSS global (Tailwind via var) */}
            <Bar dataKey="value" fill="var(--primary)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </WrapperGrafico>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4 text-primary">4. Wrapper Mapa (Leaflet)</h2>
        <WrapperMapa height={400}>
          <Marker position={[-13.5358, -71.8797]}>
            <Popup>
              Municipalidad Distrital de San Jerónimo.
            </Popup>
          </Marker>
        </WrapperMapa>
      </section>
    </div>
  );
}
