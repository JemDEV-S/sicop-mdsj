import { useState, useEffect } from 'react';
import { refreshAuthToken, getAccessToken } from '../../../lib/api-client';

export function useAuth() {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Si ya tenemos token, no hace falta rehidratar
    if (getAccessToken()) {
      setIsAuthenticated(true);
      setIsLoading(false);
      return;
    }

    refreshAuthToken()
      .then(() => {
        setIsAuthenticated(true);
      })
      .catch(() => {
        setIsAuthenticated(false);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  return { isAuthenticated, isLoading };
}
