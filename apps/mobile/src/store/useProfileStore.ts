/**
 * Profile Store — manages astrology birth profiles.
 *
 * Port of apps/web/src/store/useProfileStore.ts with the same
 * optimistic-update + background API sync pattern.
 */

import { create } from 'zustand';
import { apiFetch } from '../lib/api-client';

export interface Profile {
  id: string;
  name: string;
  relation: string;
  birthDate: string;
  birthTime: string;
  birthPlace: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
  isDefault: boolean;
}

interface ProfileState {
  profiles: Profile[];
  selectedProfileId: string | null;
  isLoading: boolean;

  fetchProfiles: () => Promise<void>;
  setSelectedProfileId: (id: string | null) => void;
  addProfile: (profile: Omit<Profile, 'id'> & { id?: string }) => Promise<void>;
  updateProfile: (id: string, updates: Partial<Profile>) => Promise<void>;
  deleteProfile: (id: string) => Promise<void>;
  getSelectedProfile: () => Profile | undefined;
}

export const useProfileStore = create<ProfileState>((set, get) => ({
  profiles: [],
  selectedProfileId: null,
  isLoading: false,

  fetchProfiles: async () => {
    set({ isLoading: true });
    try {
      const profilesData = await apiFetch<Profile[]>('/profiles');
      if (profilesData && Array.isArray(profilesData)) {
        set({
          profiles: profilesData,
          selectedProfileId:
            get().selectedProfileId ||
            (profilesData.length > 0 ? profilesData[0].id : null),
        });
      }
    } catch (err) {
      console.error('Failed to fetch profiles:', err);
    } finally {
      set({ isLoading: false });
    }
  },

  setSelectedProfileId: (selectedProfileId) => set({ selectedProfileId }),

  addProfile: async (profile) => {
    const id = profile.id || Math.random().toString(36).substring(7);
    const newProfile = { ...profile, id } as Profile;

    // Optimistic update
    set((state) => ({
      profiles: [...state.profiles, newProfile],
      selectedProfileId: state.selectedProfileId || id,
    }));

    // Sync to API
    try {
      await apiFetch('/profiles', {
        method: 'POST',
        json: newProfile,
      });
    } catch (err) {
      console.error('Failed to save profile:', err);
    }
  },

  updateProfile: async (id, updates) => {
    let updatedProfile: Profile | null = null;

    set((state) => ({
      profiles: state.profiles.map((p) => {
        if (p.id === id) {
          updatedProfile = { ...p, ...updates };
          return updatedProfile;
        }
        return p;
      }),
    }));

    if (updatedProfile) {
      try {
        await apiFetch('/profiles', {
          method: 'POST',
          json: updatedProfile,
        });
      } catch (err) {
        console.error('Failed to update profile:', err);
      }
    }
  },

  deleteProfile: async (id) => {
    set((state) => {
      const filtered = state.profiles.filter((p) => p.id !== id);
      return {
        profiles: filtered,
        selectedProfileId:
          state.selectedProfileId === id
            ? filtered[0]?.id || null
            : state.selectedProfileId,
      };
    });

    try {
      await apiFetch(`/profiles/${id}`, { method: 'DELETE' });
    } catch (err) {
      console.error('Failed to delete profile:', err);
    }
  },

  getSelectedProfile: () => {
    const { profiles, selectedProfileId } = get();
    return profiles.find((p) => p.id === selectedProfileId);
  },
}));
