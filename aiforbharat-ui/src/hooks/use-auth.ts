"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import { useAppStore } from "@/lib/store";
import type {
  ApiResponse,
  AuthTokens,
  LoginRequest,
  RegisterRequest,
  UserProfile,
  ProfileUpdateRequest,
  OtpSendRequest,
  OtpSendResponse,
  OtpVerifyRequest,
  OtpVerifyResponse,
  IdentityCreateRequest,
  IdentityResponse,
} from "@/types/api";

/**
 * Auth & Identity React Query Hooks
 * ===================================
 * Wires frontend to E1 (Login/Register), E2 (Identity), and E0 (Orchestrator /onboard).
 * All calls route through localhost:8000/api/v1.
 *
 * Constraints:
 *  - No AWS Cognito, no DigiLocker
 *  - OTP logged to backend console (local mode)
 *  - Identity verification stubbed as "Verified"
 */

// ── Login ────────────────────────────────────────────────────────────────────

export function useLogin() {
  const router = useRouter();
  const login = useAppStore((s) => s.login);

  return useMutation({
    mutationFn: async (data: LoginRequest) => {
      const res = await apiClient.post<ApiResponse<AuthTokens>>(
        "/auth/login",
        data
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      login(data.access_token, data.refresh_token, {
        user_id: data.user_id,
        name: data.name,
        phone: "",
        language_preference: "en",
      });
      toast.success("Login successful", {
        description: `Welcome back, ${data.name}!`,
      });
      router.push("/");
    },
    onError: (error: unknown) => {
      const msg =
        (error as { response?: { data?: { message?: string } } })?.response
          ?.data?.message || "Login failed. Please check your credentials.";
      toast.error("Login failed", { description: msg });
    },
  });
}

// ── Register ─────────────────────────────────────────────────────────────────

export function useRegister() {
  const router = useRouter();
  const login = useAppStore((s) => s.login);

  return useMutation({
    mutationFn: async (data: RegisterRequest) => {
      const res = await apiClient.post<ApiResponse<AuthTokens>>(
        "/auth/register",
        data
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      login(data.access_token, data.refresh_token, {
        user_id: data.user_id,
        name: data.name,
        phone: "",
        language_preference: "en",
      });
      toast.success("Account created!", {
        description: "Welcome to AIforBharat.",
      });
      router.push("/");
    },
    onError: (error: unknown) => {
      const msg =
        (error as { response?: { data?: { message?: string } } })?.response
          ?.data?.message || "Registration failed.";
      toast.error("Registration failed", { description: msg });
    },
  });
}

// ── Onboard (Orchestrator composite route) ───────────────────────────────────
// POST /api/v1/onboard → E1 register → E2 identity → E4 metadata → E5 store → E15 eligibility → E12 profile

export function useOnboard() {
  const router = useRouter();
  const login = useAppStore((s) => s.login);

  return useMutation({
    mutationFn: async (
      data: RegisterRequest & { email?: string; dob?: string }
    ) => {
      const res = await apiClient.post<
        ApiResponse<{
          user_id: string;
          name: string;
          access_token: string;
          refresh_token: string;
          identity_token?: string;
          eligibility_results?: unknown;
          degraded_services?: string[];
        }>
      >("/onboard", data);
      return res.data.data;
    },
    onSuccess: (data) => {
      login(data.access_token, data.refresh_token, {
        user_id: data.user_id,
        name: data.name,
        phone: "",
        language_preference: "en",
        identity_token: data.identity_token,
      });
      toast.success("Onboarding complete!", {
        description: "Your civic profile has been created.",
      });
      if (data.degraded_services?.length) {
        toast.warning("Some services starting up", {
          description: `Degraded: ${data.degraded_services.join(", ")}`,
        });
      }
      router.push("/");
    },
    onError: (error: unknown) => {
      const msg =
        (error as { response?: { data?: { message?: string } } })?.response
          ?.data?.message || "Onboarding failed.";
      toast.error("Onboarding failed", { description: msg });
    },
  });
}

// ── OTP Send ─────────────────────────────────────────────────────────────────
// Local mode: OTP logged to backend console, not sent via SMS

export function useOtpSend() {
  return useMutation({
    mutationFn: async (data: OtpSendRequest) => {
      const res = await apiClient.post<ApiResponse<OtpSendResponse>>(
        "/auth/otp/send",
        data
      );
      return res.data.data;
    },
    onSuccess: () => {
      toast.info("OTP sent", {
        description: "Check backend console for OTP (local mode).",
      });
    },
    onError: () => {
      toast.error("Failed to send OTP");
    },
  });
}

// ── OTP Verify ───────────────────────────────────────────────────────────────

export function useOtpVerify() {
  return useMutation({
    mutationFn: async (data: OtpVerifyRequest) => {
      const res = await apiClient.post<ApiResponse<OtpVerifyResponse>>(
        "/auth/otp/verify",
        data
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      if (data.verified) {
        toast.success("Phone verified!");
      } else {
        toast.error("Invalid OTP");
      }
    },
    onError: () => {
      toast.error("OTP verification failed");
    },
  });
}

// ── Logout ───────────────────────────────────────────────────────────────────

export function useLogout() {
  const router = useRouter();
  const logout = useAppStore((s) => s.logout);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await apiClient.post("/auth/logout");
    },
    onSuccess: () => {
      logout();
      queryClient.clear();
      toast.success("Logged out");
      router.push("/login");
    },
    onError: () => {
      // Even if API call fails, clear local state
      logout();
      queryClient.clear();
      router.push("/login");
    },
  });
}

// ── Get Current User (GET /auth/me) ──────────────────────────────────────────

export function useCurrentUser() {
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);
  const setUser = useAppStore((s) => s.setUser);

  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<UserProfile>>("/auth/me");
      setUser({
        ...res.data.data,
        language_preference: res.data.data.language_preference || "en",
      });
      return res.data.data;
    },
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000,
  });
}

// ── Update Profile (PUT /auth/profile) ───────────────────────────────────────

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ProfileUpdateRequest) => {
      const res = await apiClient.put<
        ApiResponse<{ user_id: string; updated_fields: string[] }>
      >("/auth/profile", data);
      return res.data.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      toast.success("Profile updated", {
        description: `Updated: ${data.updated_fields.join(", ")}`,
      });
    },
    onError: () => {
      toast.error("Failed to update profile");
    },
  });
}

// ── Identity Vault: Create ──────────────────────────────────────────────────

export function useCreateIdentity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: IdentityCreateRequest) => {
      const res = await apiClient.post<
        ApiResponse<{ identity_token: string; user_id: string }>
      >("/identity/create", data);
      return res.data.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["identity"] });
      toast.success("Identity vault created", {
        description: `Token: ${data.identity_token.slice(0, 8)}...`,
      });
    },
    onError: () => {
      toast.error("Failed to create identity vault");
    },
  });
}

// ── Identity Vault: Retrieve ─────────────────────────────────────────────────

export function useIdentity(token: string | undefined) {
  return useQuery({
    queryKey: ["identity", token],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<IdentityResponse>>(
        `/identity/${token}`
      );
      return res.data.data;
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });
}
