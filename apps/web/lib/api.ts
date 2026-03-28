/** ReelForge AI — API client for backend communication */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions {
  method?: string;
  body?: any;
  token?: string;
  headers?: Record<string, string>;
}

export async function api<T = any>(
  endpoint: string,
  options: ApiOptions = {}
): Promise<T> {
  const { method = "GET", body, token, headers = {} } = options;

  const config: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "An error occurred" }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// ── Job API ──
export const jobsApi = {
  createAuto: (data: { media_ids: string[]; niche?: string; region?: string }, token: string) =>
    api("/api/v1/jobs/auto", { method: "POST", body: data, token }),

  createClone: (data: { inspiration_media_id: string; user_media_ids: string[] }, token: string) =>
    api("/api/v1/jobs/clone", { method: "POST", body: data, token }),

  get: (jobId: string, token: string) =>
    api(`/api/v1/jobs/${jobId}`, { token }),

  list: (page: number, token: string) =>
    api(`/api/v1/jobs?page=${page}`, { token }),

  getBlueprint: (jobId: string, token: string) =>
    api(`/api/v1/jobs/${jobId}/blueprint`, { token }),
};

// ── Reel API ──
export const reelsApi = {
  get: (reelId: string, token: string) =>
    api(`/api/v1/reels/${reelId}`, { token }),

  regenerate: (reelId: string, token: string) =>
    api(`/api/v1/reels/${reelId}/regenerate`, { method: "POST", body: { regeneration_number: 1 }, token }),

  share: (reelId: string, token: string) =>
    api(`/api/v1/reels/${reelId}/share`, { method: "POST", token }),
};

// ── Vault API ──
export const vaultApi = {
  list: (params: { page?: number; type?: string; mood?: string }, token: string) => {
    const query = new URLSearchParams();
    if (params.page) query.set("page", String(params.page));
    if (params.type) query.set("type", params.type);
    if (params.mood) query.set("mood", params.mood);
    return api(`/api/v1/vault?${query}`, { token });
  },
};

// ── Trends API ──
export const trendsApi = {
  list: (params?: { niche?: string; region?: string }) => {
    const query = new URLSearchParams();
    if (params?.niche) query.set("niche", params.niche);
    if (params?.region) query.set("region", params.region);
    return api(`/api/v1/trends?${query}`);
  },

  niches: () => api("/api/v1/trends/niches"),
};

// ── Upload API ──
export const uploadApi = {
  initiate: (data: { filename: string; file_size: number; content_type: string }, token: string) =>
    api("/api/v1/upload/initiate", { method: "POST", body: data, token }),

  direct: async (file: File, token: string) => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE}/api/v1/upload/direct`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    if (!response.ok) throw new Error("Upload failed");
    return response.json();
  },
};
