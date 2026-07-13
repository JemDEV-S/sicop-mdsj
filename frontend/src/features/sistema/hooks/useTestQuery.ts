import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api-client';

export function useTestQuery() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await apiClient.get('/health');
      return data;
    },
  });
}
