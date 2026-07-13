import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

function App() {
  return (
    <div className="flex min-h-svh items-center justify-center p-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Bootstrap del proyecto</CardTitle>
          <CardDescription>
            React, Vite, TypeScript, Tailwind CSS y componentes base ya
            configurados con la paleta institucional.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex gap-2">
            <span className="h-8 flex-1 rounded-md bg-primary" />
            <span className="h-8 flex-1 rounded-md bg-secondary" />
            <span className="h-8 flex-1 rounded-md bg-accent" />
          </div>
          <p className="text-sm text-muted-foreground">
            Tarea T-31 completada. Base lista para continuar con el cliente
            de API y el enrutamiento.
          </p>
          <Button>Continuar</Button>
        </CardContent>
      </Card>
    </div>
  )
}

export default App
