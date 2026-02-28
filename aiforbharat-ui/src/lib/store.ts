import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * AIforBharat — Global Zustand Store
 * =====================================
 * Manages client-side state:
 *  - User session (auth tokens, user info)
 *  - Theme preference (light/dark)
 *  - Sidebar state
 *
 * Rules:
 *  - JWT stored in localStorage via persist middleware
 *  - No server-side state here — use React Query for engine data
 */

// ── Types ────────────────────────────────────────────────────────────────────

export interface UserProfile {
  user_id: string;
  name: string;
  phone: string;
  email?: string;
  state?: string;
  district?: string;
  language_preference: string;
  roles?: string[];
  identity_token?: string;
}

interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  user: UserProfile | null;
}

interface ThemeState {
  theme: "light" | "dark" | "system";
}

interface HydrationState {
  _hasHydrated: boolean;
  setHasHydrated: (v: boolean) => void;
}

interface AppState extends AuthState, ThemeState, HydrationState {
  // Auth actions
  login: (accessToken: string, refreshToken: string, user: UserProfile) => void;
  logout: () => void;
  setUser: (user: UserProfile) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;

  // Theme actions
  setTheme: (theme: "light" | "dark" | "system") => void;
}

// ── Store ────────────────────────────────────────────────────────────────────

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Hydration flag (false until Zustand persist rehydrates from localStorage)
      _hasHydrated: false,
      setHasHydrated: (v: boolean) => set({ _hasHydrated: v }),

      // Initial auth state
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      user: null,

      // Initial theme
      theme: "system",

      // Auth actions
      login: (accessToken, refreshToken, user) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", accessToken);
          localStorage.setItem("refresh_token", refreshToken);
        }
        set({
          isAuthenticated: true,
          accessToken,
          refreshToken,
          user,
        });
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
        set({
          isAuthenticated: false,
          accessToken: null,
          refreshToken: null,
          user: null,
        });
      },

      setUser: (user) => set({ user }),

      setTokens: (accessToken, refreshToken) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", accessToken);
          localStorage.setItem("refresh_token", refreshToken);
        }
        set({ accessToken, refreshToken });
      },

      // Theme actions
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "aiforbharat-store",
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        theme: state.theme,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
