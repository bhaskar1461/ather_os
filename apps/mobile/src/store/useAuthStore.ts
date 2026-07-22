/**
 * Auth Store — manages authentication state for the mobile app.
 *
 * Port of apps/web/src/store/useAuthStore.ts with secure storage
 * hydration instead of localStorage persistence.
 */

import { create } from 'zustand';
import { apiFetch, AuthExpiredError } from '../lib/api-client';
import { setTokens, clearTokens, getAccessToken, getRefreshToken } from '../lib/secure-storage';

export interface User {
  id: string;
  email: string;
  role: string;
  is_verified: boolean;
  created_at?: string;
}

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  created_at?: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  workspace_id: string;
  created_at?: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  currentWorkspace: Workspace | null;
  currentProject: Project | null;
  workspaces: Workspace[];
  projects: Project[];
  isHydrated: boolean;
  isLoading: boolean;

  // Actions
  setAuth: (token: string, refreshToken: string, user: User) => Promise<void>;
  clearAuth: () => Promise<void>;
  setUser: (user: User) => void;
  setCurrentWorkspace: (workspace: Workspace | null) => void;
  setCurrentProject: (project: Project | null) => void;
  setWorkspaces: (workspaces: Workspace[]) => void;
  setProjects: (projects: Project[]) => void;
  hydrate: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchWorkspacesAndProjects: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  refreshToken: null,
  user: null,
  currentWorkspace: null,
  currentProject: null,
  workspaces: [],
  projects: [],
  isHydrated: false,
  isLoading: false,

  setAuth: async (token, refreshToken, user) => {
    await setTokens(token, refreshToken);
    set({ token, refreshToken, user });
  },

  clearAuth: async () => {
    await clearTokens();
    set({
      token: null,
      refreshToken: null,
      user: null,
      currentWorkspace: null,
      currentProject: null,
      workspaces: [],
      projects: [],
    });
  },

  setUser: (user) => set({ user }),
  setCurrentWorkspace: (currentWorkspace) => set({ currentWorkspace, currentProject: null }),
  setCurrentProject: (currentProject) => set({ currentProject }),
  setWorkspaces: (workspaces) => set({ workspaces }),
  setProjects: (projects) => set({ projects }),

  hydrate: async () => {
    try {
      const token = await getAccessToken();
      const refreshToken = await getRefreshToken();

      if (token) {
        set({ token, refreshToken });
        // Verify token by fetching user profile
        try {
          const user = await apiFetch<User>('/auth/me');
          set({ user, isHydrated: true });
        } catch (e) {
          if (e instanceof AuthExpiredError) {
            await clearTokens();
            set({ token: null, refreshToken: null, isHydrated: true });
          } else {
            set({ isHydrated: true });
          }
        }
      } else {
        set({ isHydrated: true });
      }
    } catch {
      set({ isHydrated: true });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const data = await apiFetch<{
        access_token: string;
        refresh_token: string;
        token_type: string;
        expires_in: number;
      }>('/auth/login', {
        method: 'POST',
        json: { email, password },
      });

      await setTokens(data.access_token, data.refresh_token);
      set({ token: data.access_token, refreshToken: data.refresh_token });

      const user = await apiFetch<User>('/auth/me');
      set({ user });
    } finally {
      set({ isLoading: false });
    }
  },

  register: async (email, password, name) => {
    set({ isLoading: true });
    try {
      await apiFetch('/auth/register', {
        method: 'POST',
        json: { email, password, name: name || email.split('@')[0] },
      });
      // Auto-login after registration
      await get().login(email, password);
    } finally {
      set({ isLoading: false });
    }
  },

  logout: async () => {
    const { refreshToken } = get();
    try {
      if (refreshToken) {
        await apiFetch('/auth/logout', {
          method: 'POST',
          json: { refresh_token: refreshToken },
        });
      }
    } catch {
      // Best-effort logout
    }
    await get().clearAuth();
  },

  fetchWorkspacesAndProjects: async () => {
    try {
      const workspaces = await apiFetch<Workspace[]>('/workspaces');
      set({ workspaces });

      if (workspaces.length > 0) {
        const ws = workspaces[0];
        set({ currentWorkspace: ws });

        const projects = await apiFetch<Project[]>(`/workspaces/${ws.id}/projects`);
        set({ projects });

        if (projects.length > 0) {
          set({ currentProject: projects[0] });
        }
      }
    } catch (e) {
      console.warn('Failed to fetch workspaces:', e);
    }
  },
}));
