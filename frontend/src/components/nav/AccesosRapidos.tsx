import { Link } from 'react-router-dom';
import { ArrowRight, type LucideIcon } from 'lucide-react';

export interface AccesoRapido {
  label: string;
  href: string;
  icono: LucideIcon;
}

interface AccesosRapidosProps {
  items: AccesoRapido[];
}

export function AccesosRapidos({ items }: AccesosRapidosProps) {
  return (
    <div className="flex flex-wrap gap-3" data-testid="accesos-rapidos">
      {items.map((item) => {
        const Icono = item.icono;
        return (
          <Link
            key={item.label}
            to={item.href}
            className="inline-flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-md text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Icono className="w-4 h-4" aria-hidden="true" />
            {item.label}
            <ArrowRight className="w-3 h-3 ml-1 text-muted-foreground" aria-hidden="true" />
          </Link>
        );
      })}
    </div>
  );
}

export default AccesosRapidos;
