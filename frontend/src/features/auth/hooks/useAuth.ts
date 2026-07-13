import { useAuthStore } from '../../../store/auth';

export function useAuth() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const isLoading = useAuthStore(state => state.isLoading);
  
  return { isAuthenticated, isLoading };
}
