import { useAuthStore } from '../../../store/auth';

export function useRole(): string | undefined {
  return useAuthStore(state => state.user?.rol);
}
