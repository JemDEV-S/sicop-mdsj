import { useState } from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import {
  AlertTriangle,
  BarChart3,
  Building2,
  Download,
  Filter,
  GitBranch,
  Inbox,
  Wallet,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { Marker, Popup } from 'react-leaflet';

import Semaforo from '@/components/Semaforo';
import { DataTable } from '@/components/tabla/DataTable';
import WrapperGrafico from '@/components/grafico/WrapperGrafico';
import WrapperMapa from '@/components/mapa/WrapperMapa';

import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import {
  SkeletonCard,
  SkeletonKPI,
  SkeletonTable,
  SkeletonGrafico,
} from '@/components/layout/LoadingSkeleton';
import { FiltroChips, type FiltroChip } from '@/components/forms/FiltroChips';
import { KpiCard } from '@/components/KpiCard';
import { Button } from '@/components/ui/button';

interface Fila {
  id: number;
  obra: string;
  avance: number;
}

export default function Sandbox() {
  const [chips, setChips] = useState<FiltroChip[]>([
    { id: 'funcion', label: 'Función: Salud', onRemove: () => quitarChip('funcion') },
    { id: 'anio', label: 'Año: 2026', onRemove: () => quitarChip('anio') },
    { id: 'estancado', label: 'Estancado', onRemove: () => quitarChip('estancado') },
  ]);

  function quitarChip(id: string) {
    setChips((prev) => prev.filter((c) => c.id !== id));
  }

  const data: Fila[] = [
    { id: 1, obra: 'Colegio A', avance: 95 },
    { id: 2, obra: 'Veredas B', avance: 60 },
    { id: 3, obra: 'Parque C', avance: 20 },
  ];

  const columns: ColumnDef<Fila>[] = [
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
    <div className="p-6 space-y-10 bg-background min-h-screen">
      <PageHeader
        titulo="Sandbox de componentes"
        descripcion="Entorno de validación del design system institucional. Referencia visual para el resto del frontend."
        acciones={
          <>
            <Button variant="outline">
              <Filter className="w-4 h-4" aria-hidden="true" />
              Filtros
            </Button>
            <Button>
              <Download className="w-4 h-4" aria-hidden="true" />
              Descargar
            </Button>
          </>
        }
      />

      {/* KPIs */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">KPI cards</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="PIM 2026"
            valor="S/ 82.4 M"
            ayuda="Presupuesto institucional modificado"
            icono={Wallet}
            tono="primario"
          />
          <KpiCard
            label="Devengado"
            valor="S/ 46.1 M"
            ayuda="Ejecución acumulada al mes"
            icono={BarChart3}
            tono="secundario"
          />
          <KpiCard
            label="Ejecución"
            valor="56%"
            icono={GitBranch}
            tono="acento"
            semaforo={<Semaforo estado="alerta" texto="Atención" />}
          />
          <KpiCard
            label="Metas rezagadas"
            valor="12"
            ayuda="Devengado por debajo del umbral"
            icono={AlertTriangle}
            tono="destructivo"
          />
        </div>
      </section>

      {/* Chips de filtros */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Chips de filtros activos</h2>
        <FiltroChips
          chips={chips}
          onLimpiarTodos={() => setChips([])}
        />
        {chips.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No hay filtros activos. Recarga la página para ver el ejemplo.
          </p>
        ) : null}
      </section>

      {/* Section cards */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Section cards</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SectionCard
            titulo="Sin encabezado"
            icono={Building2}
          >
            <p className="text-sm text-muted-foreground">
              Contenido de la tarjeta. Padding medio por defecto.
            </p>
          </SectionCard>

          <SectionCard
            titulo="Con acción"
            icono={BarChart3}
            accion={
              <Button variant="link" size="sm">
                Ver todo
              </Button>
            }
          >
            <p className="text-sm text-muted-foreground">
              Tarjeta con acción a la derecha del título.
            </p>
          </SectionCard>
        </div>
      </section>

      {/* Semáforos */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Semáforos</h2>
        <div className="flex flex-wrap gap-3">
          <Semaforo estado="ok" texto="Al día" />
          <Semaforo estado="alerta" texto="Atención" />
          <Semaforo estado="critico" texto="Crítico" />
        </div>
      </section>

      {/* Estados vacíos y de error */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Estados vacío y error</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SectionCard titulo="Estado vacío">
            <EmptyState
              icono={Inbox}
              titulo="No hay pedidos que mostrar"
              descripcion="Ajusta los filtros o prueba con otro rango de fechas."
              accion={{ label: 'Limpiar filtros', onClick: () => setChips([]) }}
            />
          </SectionCard>

          <SectionCard titulo="Estado de error">
            <ErrorState
              titulo="No se pudo cargar la información"
              descripcion="Verifica tu conexión e intenta de nuevo."
              onReintentar={() => window.location.reload()}
            />
          </SectionCard>
        </div>
      </section>

      {/* Skeletons */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Skeletons de carga</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SkeletonCard />
          <SkeletonKPI />
        </div>
        <SkeletonTable rows={4} cols={5} />
        <SkeletonGrafico alto={200} />
      </section>

      {/* DataTable */}
      <SectionCard titulo="DataTable" icono={BarChart3}>
        <DataTable columns={columns} data={data} />
      </SectionCard>

      {/* Gráfico */}
      <SectionCard titulo="Gráfico (Recharts)" icono={BarChart3}>
        <WrapperGrafico>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
            <XAxis dataKey="name" axisLine={false} tickLine={false} />
            <YAxis axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: 'var(--muted)' }}
              contentStyle={{
                backgroundColor: 'var(--card)',
                borderRadius: '8px',
                border: '1px solid var(--border)',
              }}
            />
            <Bar dataKey="value" fill="var(--primary)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </WrapperGrafico>
      </SectionCard>

      {/* Mapa */}
      <SectionCard titulo="Mapa (Leaflet)" icono={Building2}>
        <WrapperMapa height={400}>
          <Marker position={[-13.5358, -71.8797]}>
            <Popup>Municipalidad Distrital de San Jerónimo.</Popup>
          </Marker>
        </WrapperMapa>
      </SectionCard>
    </div>
  );
}
