import axios, { type AxiosError } from "axios";
import { toast } from "sonner";

/**
 * AIforBharat — Axios API Client
 * ================================
 * Single instance pointing to the local API Gateway on port 8000.
 * All engine communication goes through this client.
 *
 * Rules:
 *  - Base URL: http://localhost:8000/api/v1
 *  - Auth: Bearer JWT from localStorage (auto-attached via interceptor)
 *  - No AWS, no S3 URLs, no external services
 *  - Timeout: 15s (strict to prevent UI hang)
 */

const API_BASE_URL = "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request Interceptor: Attach JWT ──────────────────────────────────────────
apiClient.interceptors.request.use(
  (config) => {
    // Public endpoints that don't require auth
    const publicPaths = [
      "/auth/login",
      "/auth/register",
      "/auth/otp/send",
      "/auth/otp/verify",
      "/auth/token/refresh",
      "/onboard",
      "/voice-query",
    ];

    const isPublic = publicPaths.some((path) =>
      config.url?.startsWith(path)
    );

    if (!isPublic) {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("access_token")
          : null;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: Handle errors globally ─────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Auto-refresh on 401 (token expired)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken =
          typeof window !== "undefined"
            ? localStorage.getItem("refresh_token")
            : null;

        if (refreshToken) {
          const res = await axios.post(`${API_BASE_URL}/auth/token/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = res.data.data;

          if (typeof window !== "undefined") {
            localStorage.setItem("access_token", access_token);
            localStorage.setItem("refresh_token", refresh_token);
          }

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        }
      } catch {
        // Refresh failed — clear tokens, user must re-login
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      }
    }

    // ── Global 404 handler (e.g. Policy Ingestion route not found) ─────────
    if (error.response?.status === 404) {
      const url = error.config?.url ?? "unknown endpoint";

      // Policy ingestion specific message
      if (url.includes("ingest-policy") || url.includes("policy")) {
        toast.warning("Policy Unavailable", {
          description:
            "External URL scraping is disabled in local mode. Utilizing mock policies instead.",
        });
      } else {
        toast.error("Resource Not Found", {
          description: `The endpoint ${url} returned 404. Please verify the backend engine is running.`,
        });
      }
    }

    // ── Global timeout handler ──────────────────────────────────────────────
    if (error.code === "ECONNABORTED") {
      toast.error("Request Timeout", {
        description:
          "The backend took too long to respond. Please ensure all engines are running on localhost:8000.",
      });
    }

    return Promise.reject(error);
  }
);

export default apiClient;
export { API_BASE_URL };
