import MapaObras from '../../features/obras/MapaObras';

export default function Mapa() {
  return (
    <div className="container py-8 max-w-[1400px]">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Mapa de Obras Públicas</h1>
        <p className="text-muted-foreground mt-2">
          Ubicación y estado de ejecución de las inversiones en el distrito de San Jerónimo.
        </p>
      </div>
      <MapaObras />
    </div>
  );
}
