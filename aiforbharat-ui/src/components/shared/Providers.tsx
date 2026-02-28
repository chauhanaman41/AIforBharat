"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { NextUIProvider } from "@nextui-org/react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SmoothScrollProvider } from "@/components/shared/SmoothScrollProvider";
import { AuthGuard } from "@/components/shared/AuthGuard";

/**
 * Providers — Wraps the entire application with required context providers.
 *
 * Stack (outer → inner):
 *  1. QueryClientProvider — React Query for server state (caching: 5min, stale: 1min)
 *  2. NextUIProvider (Hero UI) — Component library theming
 *  3. TooltipProvider — ShadCN tooltip context
 *  4. SmoothScrollProvider — Lenis smooth scroll
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 1 * 60 * 1000, // 1 minute
            gcTime: 5 * 60 * 1000, // 5 minutes (was cacheTime)
            retry: 2,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <NextUIProvider>
        <TooltipProvider delayDuration={200}>
          <SmoothScrollProvider>
            <AuthGuard>{children}</AuthGuard>
            <Toaster position="bottom-right" richColors closeButton />
          </SmoothScrollProvider>
        </TooltipProvider>
      </NextUIProvider>
    </QueryClientProvider>
  );
}
