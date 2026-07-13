import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Table as TableIcon } from 'lucide-react';
import {
  useEjecucionResumen,
  useEjecucionPorFuncion,
  useEjecucionPorFuente,
  useEjecucionMensual,
} from '@/features/ejecucion/hooks';
import ResumenKpis from '@/features/ejecucion/secciones/ResumenKpis';
import GraficoFuncion from '@/features/ejecucion/secciones/GraficoFuncion';
import GraficoFuente from '@/features/ejecucion/secciones/GraficoFuente';
import GraficoMensual from '@/features/ejecucion/secciones/GraficoMensual';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const ANO_VIGENTE = 2026;
const ANOS_DISPONIBLES = [ANO_VIGENTE, ANO_VIGENTE - 1, ANO_VIGENTE - 2, ANO_VIGENTE - 3];

export default function EjecucionDashboard() {
  const [ano, setAno] = useState<number>(ANO_VIGENTE);

  const { data: resumenData, isLoading: loadingResumen } = useEjecucionResumen({ ano });
  const { data: funcionData, isLoading: loadingFuncion } = useEjecucionPorFuncion({ ano });
  const { data: fuenteData, isLoading: loadingFuente } = useEjecucionPorFuente({ ano });
  const { data: mensualData, isLoading: loadingMensual } = useEjecucionMensual({ ano });

  return (
    <div className="mx-auto max-w-6xl px-4 md:px-6 py-8">
      <PageHeader
        titulo="Ejecución Presupuestal"
        descripcion="Cómo se distribuye y ejecuta el presupuesto del distrito. Datos oficiales del SIAF."
        densidad="publico"
        acciones={
          <>
            <Select value={ano.toString()} onValueChange={(v) => setAno(parseInt(v, 10))}>
              <SelectTrigger className="w-32" aria-label="Año de ejecución">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ANOS_DISPONIBLES.map((a) => (
                  <SelectItem key={a} value={a.toString()}>
                    Año {a}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button asChild variant="outline">
              <Link to="/ejecucion/detalle">
                <TableIcon className="w-4 h-4" aria-hidden="true" />
                Ver detalle por meta
              </Link>
            </Button>
          </>
        }
      />

      <div className="space-y-6">
        <ResumenKpis data={resumenData} isLoading={loadingResumen} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <GraficoFuncion data={funcionData} isLoading={loadingFuncion} />
          <GraficoFuente data={fuenteData} isLoading={loadingFuente} />
        </div>

        <GraficoMensual data={mensualData} isLoading={loadingMensual} />
      </div>
    </div>
  );
}
