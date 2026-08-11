import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Eye, EyeOff, Loader2, Lock, LogIn, ShieldCheck, User } from 'lucide-react';
import { useAuthStore } from '../../store/auth';
import { handleApiError } from '../../lib/api-errors';
import { GrecaAndina } from '@/components/decor/GrecaAndina';
import { cn } from '@/lib/utils';
import logoMdsj from '@/assets/logo.png';

export default function Login() {
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [verPassword, setVerPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await login(usuario, password);
      navigate('/interno', { replace: true });
    } catch (error) {
      setErrorMsg(handleApiError(error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="min-h-screen bg-background grid lg:grid-cols-2 overflow-x-hidden"
      data-testid="login-content"
    >
      {/* Panel de marca (izquierda, solo desktop) */}
      <aside className="relative hidden lg:flex flex-col justify-between overflow-hidden bg-primary text-primary-foreground p-12">
        {/* Textura sutil de fondo */}
        <div
          aria-hidden="true"
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)',
            backgroundSize: '24px 24px',
          }}
        />

        <div className="relative flex items-center gap-3">
          <img
            src={logoMdsj}
            alt="Escudo de la Municipalidad Distrital de San Jerónimo"
            className="h-12 w-12 object-contain"
          />
          <div className="leading-tight">
            <p className="text-sm font-semibold">Municipalidad de San Jerónimo</p>
            <p className="text-xs text-primary-foreground/70">Cusco, Perú</p>
          </div>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-3xl font-bold leading-tight">
            Panel interno de gestión presupuestal
          </h1>
          <p className="mt-4 text-primary-foreground/80 leading-relaxed">
            Consulta saldos, sigue el pipeline de pedidos y cruza la información
            de SIAF y SIGA en un solo lugar. Acceso exclusivo para funcionarios
            de la municipalidad.
          </p>

          <ul className="mt-8 space-y-3 text-sm">
            {[
              'Datos oficiales de fuentes autoritativas del MEF',
              'Alcance según tu rol y centro de costo',
              'Exportación y trazabilidad de cada consulta',
            ].map((texto) => (
              <li key={texto} className="flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 mt-0.5 shrink-0 text-accent" aria-hidden="true" />
                <span className="text-primary-foreground/85">{texto}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative -mx-12 -mb-12">
          <GrecaAndina color="accent" variante="escalonada" altura={10} />
        </div>
      </aside>

      {/* Panel del formulario (derecha) */}
      <main className="flex flex-col items-center justify-center px-6 py-12 md:px-10">
        <div className="w-full max-w-sm">
          {/* Branding compacto (solo móvil, ya que el panel izquierdo no se ve) */}
          <div className="lg:hidden flex flex-col items-center text-center mb-8">
            <img
              src={logoMdsj}
              alt="Escudo de la Municipalidad Distrital de San Jerónimo"
              className="h-16 w-16 object-contain"
            />
            <p className="mt-3 text-sm font-semibold text-foreground">
              Municipalidad de San Jerónimo
            </p>
          </div>

          <div className="mb-8">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              <Lock className="w-3 h-3" aria-hidden="true" />
              Acceso restringido
            </span>
            <h2 className="mt-4 text-2xl font-bold text-foreground">
              Iniciar sesión
            </h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Ingresa tus credenciales para acceder al panel interno.
            </p>
          </div>

          {errorMsg && (
            <div
              role="alert"
              className="flex items-start gap-2.5 p-3 mb-5 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md"
            >
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                className="block text-sm font-medium text-foreground mb-1.5"
                htmlFor="usuario"
              >
                Usuario
              </label>
              <div className="relative">
                <User
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
                  aria-hidden="true"
                />
                <input
                  id="usuario"
                  type="text"
                  autoComplete="username"
                  value={usuario}
                  onChange={(e) => setUsuario(e.target.value)}
                  disabled={isSubmitting}
                  required
                  className={cn(
                    'w-full h-11 pl-10 pr-3 rounded-md bg-background text-foreground',
                    'border border-input placeholder:text-muted-foreground',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-ring',
                    'disabled:opacity-60 disabled:cursor-not-allowed transition-colors',
                  )}
                  placeholder="tu.usuario"
                />
              </div>
            </div>

            <div>
              <label
                className="block text-sm font-medium text-foreground mb-1.5"
                htmlFor="password"
              >
                Contraseña
              </label>
              <div className="relative">
                <Lock
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
                  aria-hidden="true"
                />
                <input
                  id="password"
                  type={verPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  required
                  className={cn(
                    'w-full h-11 pl-10 pr-11 rounded-md bg-background text-foreground',
                    'border border-input placeholder:text-muted-foreground',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-ring',
                    'disabled:opacity-60 disabled:cursor-not-allowed transition-colors',
                  )}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setVerPassword((v) => !v)}
                  aria-label={verPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {verPassword ? (
                    <EyeOff className="w-4 h-4" aria-hidden="true" />
                  ) : (
                    <Eye className="w-4 h-4" aria-hidden="true" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                'w-full h-11 inline-flex items-center justify-center gap-2 rounded-md',
                'bg-primary text-primary-foreground font-medium shadow-sm',
                'hover:bg-primary/90 transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                'disabled:opacity-70 disabled:cursor-not-allowed',
              )}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  Ingresando...
                </>
              ) : (
                <>
                  <LogIn className="w-4 h-4" aria-hidden="true" />
                  Ingresar
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-sm text-center text-muted-foreground">
            ¿Olvidaste tu contraseña? Contacta al administrador del sistema.
          </p>

          <div className="mt-8 pt-6 border-t border-border text-center">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary transition-colors focus-visible:outline-none focus-visible:underline"
            >
              <ArrowLeft className="w-4 h-4" aria-hidden="true" />
              Volver al portal público
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
