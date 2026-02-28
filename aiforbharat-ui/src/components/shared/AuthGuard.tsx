"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAppStore } from "@/lib/store";

/**
 * AuthGuard — Client-side route protection.
 * Redirects unauthenticated users to /login.
 * Skips protection for public routes (login, register).
 *
 * Waits for Zustand persist to finish hydrating from localStorage
 * before evaluating auth state — prevents false redirect loops.
 *
 * Constraints:
 *  - No server-side middleware (Next.js middleware could do this but
 *    we keep auth fully client-side with Zustand + localStorage).
 *  - No AWS Cognito, no external auth provider checks.
 */

const PUBLIC_ROUTES = ["/login", "/register"];

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);
  const hasHydrated = useAppStore((s) => s._hasHydrated);

  const isPublicRoute = PUBLIC_ROUTES.some((route) =>
    pathname.startsWith(route)
  );

  useEffect(() => {
    // Only redirect AFTER Zustand has rehydrated persisted state
    if (hasHydrated && !isAuthenticated && !isPublicRoute) {
      router.replace("/login");
    }
  }, [hasHydrated, isAuthenticated, isPublicRoute, router]);

  // On public routes, always render immediately
  if (isPublicRoute) return <>{children}</>;

  // While Zustand is still hydrating, show a brief loading state
  if (!hasHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Hydrated but not authenticated — render nothing (redirect will fire)
  if (!isAuthenticated) return null;

  return <>{children}</>;
}
