import { type AxiosError } from 'axios';

// Traducciones comunes de errores Pydantic (FastAPI) al español llano, 
// respetando el tono institucional y evitando jerga técnica.
const PYDANTIC_TRANSLATIONS: Record<string, string> = {
  'field required': 'Este campo es obligatorio.',
  'value is not a valid email address': 'El formato del correo electrónico no es válido.',
  'value is not a valid email address: The email address is not valid. It must have exactly one @-sign.': 'El formato del correo electrónico no es válido.',
  'string too short': 'El texto ingresado es demasiado corto.',
  'string too long': 'El texto ingresado es demasiado largo.',
  'value must be a valid integer': 'Debes ingresar un número entero válido.',
  'value must be a valid number': 'Debes ingresar un número válido.'
};

export class ApiError extends Error {
  public status: number;
  public details: unknown;

  constructor(message: string, status: number = 500, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export function handleApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    const axiosError = error as AxiosError;
    const status = axiosError.response?.status || 500;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = axiosError.response?.data as any;

    if (data && data.detail) {
      // Caso 1: FastAPI lanza un HTTPException genérico {"detail": "Mensaje"}
      if (typeof data.detail === 'string') {
        return new ApiError(data.detail, status, data);
      }

      // Caso 2: FastAPI (Pydantic) lanza errores de validación {"detail": [{ "loc": [...], "msg": "..." }]}
      if (Array.isArray(data.detail) && data.detail.length > 0 && data.detail[0].msg) {
        const firstError = data.detail[0];
        const rawMsg = firstError.msg;
        
        // Buscar traducción o usar un genérico (lenguaje llano)
        let finalMessage = 'Revisá los datos ingresados e intentá de nuevo.';
        
        // Buscar coincidencia exacta o parcial
        for (const [enMsg, esMsg] of Object.entries(PYDANTIC_TRANSLATIONS)) {
          if (rawMsg.includes(enMsg)) {
            finalMessage = esMsg;
            break;
          }
        }
          
        return new ApiError(finalMessage, status, data);
      }
    }

    // Errores de red u otros sin cuerpo estructurado
    if (axiosError.message === 'Network Error') {
      return new ApiError('No se pudo conectar con el servidor. Revisá tu conexión a internet.', status);
    }

    return new ApiError('Ocurrió un error inesperado. Intentá de nuevo más tarde.', status, data);
  }

  return new ApiError('Ocurrió un error inesperado. Intentá de nuevo más tarde.', 500, error);
}
