import { useTestQuery } from '../../features/sistema/hooks/useTestQuery';

export default function QueryTest() {
  const { data, isLoading, isError, error, isFetching } = useTestQuery();

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">TanStack Query Test</h1>
      
      <div className="p-6 bg-white rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold mb-4">Estado de la petición /health</h2>
        
        <div className="space-y-4 font-mono text-sm">
          <div className="flex gap-4">
            <span className="font-semibold w-24">isLoading:</span>
            <span className={isLoading ? "text-blue-600" : "text-gray-600"}>{String(isLoading)}</span>
          </div>
          
          <div className="flex gap-4">
            <span className="font-semibold w-24">isFetching:</span>
            <span className={isFetching ? "text-blue-600" : "text-gray-600"}>{String(isFetching)}</span>
          </div>
          
          <div className="flex gap-4">
            <span className="font-semibold w-24">isError:</span>
            <span className={isError ? "text-red-600" : "text-gray-600"}>{String(isError)}</span>
          </div>
          
          {error && (
            <div className="p-4 bg-red-50 text-red-700 rounded border border-red-200">
              {error.message}
            </div>
          )}
          
          <div className="mt-6 border-t pt-4">
            <span className="font-semibold block mb-2">Data:</span>
            <pre className="bg-gray-50 p-4 rounded text-gray-700 overflow-x-auto border border-gray-100">
              {JSON.stringify(data, null, 2) || 'null'}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
