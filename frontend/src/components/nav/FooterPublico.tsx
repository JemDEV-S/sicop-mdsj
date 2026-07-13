import { Link } from 'react-router-dom';
import { GrecaAndina } from '@/components/decor/GrecaAndina';
import { Building2, BarChart3, Users, MapPin, ExternalLink } from 'lucide-react';

/**
 * Footer institucional del portal público.
 * Estructura: greca decorativa · panel oscuro con branding e info · copyright.
 */
export function FooterPublico() {
  const anio = new Date().getFullYear();

  return (
    <footer className="mt-20">
      {/* Greca decorativa institucional */}
      <div className="bg-primary" aria-hidden="true">
        <GrecaAndina color="accent" variante="escalonada" altura={6} />
      </div>

      {/* Panel principal */}
      <div className="bg-primary text-primary-foreground">
        <div className="mx-auto max-w-6xl px-4 md:px-6 py-12 md:py-14">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-10">
            {/* Branding */}
            <div className="md:col-span-5">
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className="inline-flex h-11 w-11 items-center justify-center rounded-md bg-primary-foreground text-primary text-sm font-bold shrink-0"
                >
                  MDSJ
                </span>
                <div>
                  <p className="text-base font-semibold leading-tight">
                    Municipalidad Distrital de San Jerónimo
                  </p>
                  <p className="text-xs text-primary-foreground/70 mt-0.5">
                    Cusco, Perú
                  </p>
                </div>
              </div>

              <p className="mt-5 text-sm text-primary-foreground/80 leading-relaxed max-w-sm">
                Portal de Transparencia. Consulta obras públicas, ejecución del presupuesto y
                proveedores de la gestión municipal en tiempo real.
              </p>

              <a
                href="https://www.munisanjeronimo.gob.pe/"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-primary-foreground border-b border-primary-foreground/30 hover:border-primary-foreground pb-0.5 transition-colors focus-visible:outline-none focus-visible:border-primary-foreground"
              >
                Sitio web institucional
                <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
              </a>
            </div>

            {/* Navegación */}
            <div className="md:col-span-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-primary-foreground/70 mb-4">
                Explora el portal
              </p>
              <ul className="space-y-3 text-sm">
                <FooterLink to="/obras" icono={Building2} label="Directorio de obras" />
                <FooterLink to="/ejecucion" icono={BarChart3} label="Ejecución presupuestal" />
                <FooterLink to="/proveedores" icono={Users} label="Padrón de proveedores" />
                <FooterLink to="/mapa" icono={MapPin} label="Mapa del distrito" />
              </ul>
            </div>

            {/* Fuentes */}
            <div className="md:col-span-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-primary-foreground/70 mb-4">
                Fuentes de los datos
              </p>
              <ul className="space-y-2 text-sm text-primary-foreground/80">
                <li>SIAF · MEF</li>
                <li>SIGA · MEF</li>
                <li>Invierte.pe · MEF</li>
              </ul>
              <p className="mt-4 text-xs text-primary-foreground/60">
                Sincronización diaria automática.
              </p>
            </div>
          </div>

          {/* Copyright */}
          <div className="mt-12 pt-6 border-t border-primary-foreground/15 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <p className="text-xs text-primary-foreground/70">
              © {anio} Municipalidad Distrital de San Jerónimo. Todos los derechos reservados.
            </p>
            <p className="text-xs text-primary-foreground/70">
              Cumple con la Ley de Transparencia y Acceso a la Información Pública.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}

interface FooterLinkProps {
  to: string;
  icono: typeof Building2;
  label: string;
}

function FooterLink({ to, icono: Icono, label }: FooterLinkProps) {
  return (
    <li>
      <Link
        to={to}
        className="inline-flex items-center gap-2 text-primary-foreground/80 hover:text-primary-foreground focus-visible:outline-none focus-visible:underline transition-colors"
      >
        <Icono className="w-3.5 h-3.5 text-primary-foreground/60" aria-hidden="true" />
        {label}
      </Link>
    </li>
  );
}

export default FooterPublico;
