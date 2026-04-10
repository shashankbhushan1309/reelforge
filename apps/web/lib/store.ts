/** Zustand store for global state management */

import { create } from "zustand";



interface MediaItem {
  id: string;
  type: "video" | "photo";
  filename: string;
  duration_ms?: number;
  size_bytes?: number;
  status: string;
  thumbnail_url?: string;
  mood_tags?: string[];
}

interface Job {
  id: string;
  mode: "clone" | "auto";
  status: string;
  progress: number;
  created_at: string;
}

interface Reel {
  id: string;
  job_id: string;
  download_url?: string;
  square_download_url?: string;
  landscape_download_url?: string;
  thumbnail_url?: string;
  duration_ms?: number;
  share_token?: string;
  captions?: Record<string, any>;
}



interface AppState {
  // Auth
  user: any | null;
  token: string | null;
  setUser: (user: any) => void;
  setToken: (token: string | null) => void;
  logout: () => void;

  // Mode
  mode: "auto" | "clone";
  setMode: (mode: "auto" | "clone") => void;

  // Upload
  uploadedFiles: MediaItem[];
  inspirationMedia: MediaItem | null;
  addUploadedFile: (file: MediaItem) => void;
  removeUploadedFile: (id: string) => void;
  clearUploadedFiles: () => void;
  setInspirationMedia: (media: MediaItem | null) => void;

  // Jobs
  activeJob: Job | null;
  setActiveJob: (job: Job | null) => void;

  // Reel
  currentReel: Reel | null;
  setCurrentReel: (reel: Reel | null) => void;

  // UI
  niche: string;
  region: string;
  setNiche: (niche: string) => void;
  setRegion: (region: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Auth
  user: null,
  token: null,
  setUser: (user) => set({ user }),
  setToken: (token) => set({ token }),
  logout: () => set({ user: null, token: null, uploadedFiles: [], activeJob: null, currentReel: null }),

  // Mode
  mode: "auto",
  setMode: (mode) => set({ mode }),

  // Upload
  uploadedFiles: [],
  inspirationMedia: null,
  addUploadedFile: (file) =>
    set((state) => ({ uploadedFiles: [...state.uploadedFiles, file] })),
  removeUploadedFile: (id) =>
    set((state) => ({
      uploadedFiles: state.uploadedFiles.filter((f) => f.id !== id),
    })),
  clearUploadedFiles: () => set({ uploadedFiles: [] }),
  setInspirationMedia: (media) => set({ inspirationMedia: media }),

  // Jobs
  activeJob: null,
  setActiveJob: (job) => set({ activeJob: job }),

  // Reel
  currentReel: null,
  setCurrentReel: (reel) => set({ currentReel: reel }),

  // UI
  niche: "Lifestyle",
  region: "US",
  setNiche: (niche) => set({ niche }),
  setRegion: (region) => set({ region }),
}));
