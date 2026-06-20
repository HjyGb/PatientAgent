import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  employee_id: string;
  name: string;
  department: string;
  role: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;

  login: (token: string, user: User) => void;
  logout: () => void;
  setToken: (token: string | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      login: (token, user) =>
        set({ token, user, isAuthenticated: true }),

      logout: () =>
        set({ token: null, user: null, isAuthenticated: false }),

      setToken: (token) =>
        set({ token, isAuthenticated: !!token }),
    }),
    {
      name: 'patient-agent-auth',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

/** Get the current auth token (for API client). */
export function getAuthToken(): string | null {
  return useAuthStore.getState().token;
}
