import { useState } from 'react';
import { 
  useEjecucionResumen, 
  useEjecucionPorFuncion, 
  useEjecucionPorFuente, 
  useEjecucionMensual 
} from '../../features/ejecucion/hooks';
import ResumenKpis from '../../features/ejecucion/secciones/ResumenKpis';
import GraficoFuncion from '../../features/ejecucion/secciones/GraficoFuncion';
import GraficoFuente from '../../features/ejecucion/secciones/GraficoFuente';
import GraficoMensual from '../../features/ejecucion/secciones/GraficoMensual';

export default function EjecucionDashboard() {
  const [ano, setAno] = useState<number>(new Date().getFullYear());

  const { data: resumenData, isLoading: loadingResumen } = useEjecucionResumen({ ano });
  const { data: funcionData, isLoading: loadingFuncion } = useEjecucionPorFuncion({ ano });
  const { data: fuenteData, isLoading: loadingFuente } = useEjecucionPorFuente({ ano });
  const { data: mensualData, isLoading: loadingMensual } = useEjecucionMensual({ ano });

  return (
    <div className="container mx-auto py-8 px-4 flex flex-col gap-8">
      
      {/* Cabecera y Filtros */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Ejecución Presupuestal</h1>
          <p className="text-muted-foreground mt-1">
            Vista general del estado de ejecución del distrito de San Jerónimo
          </p>
        </div>
        
        <div className="flex items-center gap-4 bg-card border rounded-lg p-2 shadow-sm">
          <div className="flex items-center gap-2">
            <label htmlFor="ano-selector" className="text-sm font-medium text-muted-foreground">
              Año:
            </label>
            <select
              id="ano-selector"
              value={ano}
              onChange={(e) => setAno(Number(e.target.value))}
              className="bg-background border rounded px-2 py-1 text-sm text-foreground focus:ring-1 focus:ring-primary"
            >
              {/* Opciones futuras de años irán aquí */}
              <option value={new Date().getFullYear()}>{new Date().getFullYear()}</option>
            </select>
          </div>
          
          <div className="h-4 w-px bg-border hidden md:block"></div>
          
          <button 
            disabled 
            title="Próximamente"
            className="text-sm px-3 py-1 bg-muted text-muted-foreground rounded cursor-not-allowed border"
          >
            Tabla Detallada (HU-06)
          </button>
        </div>
      </div>

      {/* Tarjetas KPI */}
      <section>
        <ResumenKpis data={resumenData} isLoading={loadingResumen} />
      </section>

      {/* Gráficos */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <GraficoFuncion data={funcionData} isLoading={loadingFuncion} />
        <div className="flex flex-col gap-8">
          <GraficoFuente data={fuenteData} isLoading={loadingFuente} />
          {/* El gráfico mensual va debajo de la dona si se apilan en 2 columnas, 
              o podemos ponerlo full width abajo. Lo pondremos debajo de la dona para balancear 
              la altura del grafico de barras horizontal si hay muchas funciones */}
          <GraficoMensual data={mensualData} isLoading={loadingMensual} />
        </div>
      </section>

    </div>
  );
}
