"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Phone, Lock, Eye, EyeOff, ArrowRight, Loader2 } from "lucide-react";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useLogin } from "@/hooks/use-auth";

/**
 * Login Page — E1 Auth UI
 * ========================
 * ShadCN forms + UIverse glow effects + CSS Buttons styling.
 * Connects to POST /api/v1/auth/login (local gateway).
 * No DigiLocker, no AWS Cognito. Phone + password only.
 */

const loginSchema = z.object({
  phone: z
    .string()
    .min(1, "Phone number is required")
    .transform((v) => v.replace(/[\s\-+]/g, "").replace(/^91/, ""))
    .pipe(
      z.string()
        .length(10, "Phone number must be 10 digits")
        .regex(/^\d{10}$/, "Enter a valid 10-digit Indian mobile number")
    ),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const loginMutation = useLogin();

  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: "onTouched",
    defaultValues: {
      phone: "",
      password: "",
    },
  });

  function onSubmit(data: LoginFormData) {
    loginMutation.mutate(data);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      {/* Background decorative gradients */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary/5 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-chart-1/5 blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* UIverse glow card wrapper */}
        <div className="uiverse-glow">
          <Card className="border-0 shadow-2xl">
            <CardHeader className="text-center pb-2 pt-8">
              {/* Brand */}
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground font-bold text-xl shadow-lg">
                AI
              </div>
              <h1 className="text-2xl font-bold tracking-tight">
                Welcome Back
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Sign in to your Personal Civic Operating System
              </p>
            </CardHeader>

            <CardContent className="px-8 pb-8">
              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit(onSubmit)}
                  className="space-y-5"
                >
                  {/* Phone */}
                  <FormField
                    control={form.control}
                    name="phone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">
                          Phone Number
                        </FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                              placeholder="9876543210"
                              className="pl-10 h-11"
                              maxLength={10}
                              inputMode="numeric"
                              {...field}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Password */}
                  <FormField
                    control={form.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium">
                          Password
                        </FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                              type={showPassword ? "text" : "password"}
                              placeholder="••••••••"
                              className="pl-10 pr-10 h-11"
                              {...field}
                            />
                            <button
                              type="button"
                              onClick={() => setShowPassword(!showPassword)}
                              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                              aria-label={
                                showPassword ? "Hide password" : "Show password"
                              }
                            >
                              {showPassword ? (
                                <EyeOff className="h-4 w-4" />
                              ) : (
                                <Eye className="h-4 w-4" />
                              )}
                            </button>
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Submit — CSS Buttons styled */}
                  <button
                    type="submit"
                    disabled={loginMutation.isPending}
                    className="css-btn-primary w-full h-11 text-sm disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
                  >
                    {loginMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Signing in...
                      </>
                    ) : (
                      <>
                        Sign In
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </form>
              </Form>

              <Separator className="my-6" />

              {/* Register link */}
              <p className="text-center text-sm text-muted-foreground">
                Don&apos;t have an account?{" "}
                <Link
                  href="/register"
                  className="css-btn-ghost inline px-0 py-0 font-semibold text-primary"
                >
                  Create one
                </Link>
              </p>

              {/* Local mode notice */}
              <div className="mt-4 rounded-lg bg-muted/50 p-3 text-center">
                <p className="text-xs text-muted-foreground">
                  🔒 Local Mode — All data stays on your machine.
                  <br />
                  No cloud services, no external auth providers.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
