"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Phone,
  Lock,
  Eye,
  EyeOff,
  User,
  MapPin,
  Globe,
  IndianRupee,
  ArrowRight,
  Loader2,
  ShieldCheck,
} from "lucide-react";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Combobox } from "@/components/ui/combobox";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRegister, useOnboard } from "@/hooks/use-auth";

/**
 * Register / Onboard Page
 * ========================
 * Two modes:
 *   1. Quick Register → POST /api/v1/auth/register (E1 only)
 *   2. Full Onboard   → POST /api/v1/onboard (Orchestrator: E1→E2→E4→E5→E15→E12)
 *
 * ShadCN forms + UIverse glow + CSS Buttons.
 * No DigiLocker, no AWS. Local-first only.
 */

const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
  "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
  "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
];

const STATE_ITEMS = INDIAN_STATES.map((s) => ({ value: s, label: s }));

const POPULAR_DISTRICTS = [
  "Ahmedabad", "Bengaluru Urban", "Chennai", "Delhi", "Hyderabad",
  "Jaipur", "Kolkata", "Lucknow", "Mumbai", "Patna", "Pune",
  "Thiruvananthapuram", "Varanasi", "Bhopal", "Chandigarh",
  "Coimbatore", "Dehradun", "Guwahati", "Indore", "Nagpur",
  "Raipur", "Ranchi", "Surat", "Visakhapatnam",
];

const DISTRICT_ITEMS = POPULAR_DISTRICTS.map((d) => ({ value: d, label: d }));

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी (Hindi)" },
  { value: "bn", label: "বাংলা (Bengali)" },
  { value: "te", label: "తెలుగు (Telugu)" },
  { value: "mr", label: "मराठी (Marathi)" },
  { value: "ta", label: "தமிழ் (Tamil)" },
  { value: "gu", label: "ગુજરાતી (Gujarati)" },
  { value: "kn", label: "ಕನ್ನಡ (Kannada)" },
  { value: "ml", label: "മലയാളം (Malayalam)" },
  { value: "pa", label: "ਪੰਜਾਬੀ (Punjabi)" },
  { value: "or", label: "ଓଡ଼ିଆ (Odia)" },
  { value: "as", label: "অসমীয়া (Assamese)" },
];

const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  phone: z
    .string()
    .length(10, "Phone number must be exactly 10 digits")
    .regex(/^\d{10}$/, "Enter a valid 10-digit Indian mobile number"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string(),
  state: z.string().optional(),
  district: z.string().optional(),
  annual_income: z
    .string()
    .optional()
    .refine((v) => !v || (!isNaN(parseFloat(v)) && parseFloat(v) >= 0), {
      message: "Income must be a valid non-negative number",
    }),
  language_preference: z.string(),
  consent_data_processing: z.boolean().refine((v) => v === true, {
    message: "You must consent to data processing to continue",
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [mode, setMode] = useState<"quick" | "full">("full");
  const registerMutation = useRegister();
  const onboardMutation = useOnboard();

  const isPending = registerMutation.isPending || onboardMutation.isPending;

  const form = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      phone: "",
      password: "",
      confirmPassword: "",
      state: "",
      district: "",
      annual_income: "",
      language_preference: "en",
      consent_data_processing: false,
    },
  });

  function onSubmit(data: RegisterFormData) {
    const { confirmPassword, annual_income, ...rest } = data;
    void confirmPassword; // consumed by zod validation only

    const payload = {
      ...rest,
      ...(annual_income ? { annual_income: parseFloat(annual_income) } : {}),
    };

    if (mode === "full") {
      onboardMutation.mutate({
        ...payload,
        consent_data_processing: payload.consent_data_processing,
      });
    } else {
      registerMutation.mutate({
        ...payload,
        consent_data_processing: payload.consent_data_processing,
      });
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      {/* Background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-chart-2/5 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-chart-4/5 blur-3xl" />
      </div>

      <div className="w-full max-w-lg relative z-10">
        <div className="uiverse-glow">
          <Card className="border-0 shadow-2xl">
            <CardHeader className="text-center pb-2 pt-8">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground font-bold text-xl shadow-lg">
                AI
              </div>
              <h1 className="text-2xl font-bold tracking-tight">
                Join AIforBharat
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Create your Personal Civic Operating System account
              </p>
            </CardHeader>

            <CardContent className="px-8 pb-8">
              {/* Mode Tabs */}
              <Tabs
                value={mode}
                onValueChange={(v) => setMode(v as "quick" | "full")}
                className="mb-6"
              >
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="full" className="text-xs">
                    <ShieldCheck className="h-3.5 w-3.5 mr-1" />
                    Full Onboard
                  </TabsTrigger>
                  <TabsTrigger value="quick" className="text-xs">
                    Quick Register
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="full">
                  <p className="text-xs text-muted-foreground text-center">
                    Creates account + identity vault + eligibility check
                  </p>
                </TabsContent>
                <TabsContent value="quick">
                  <p className="text-xs text-muted-foreground text-center">
                    Creates account only — set up vault later
                  </p>
                </TabsContent>
              </Tabs>

              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit(onSubmit)}
                  className="space-y-4"
                >
                  {/* Name */}
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Full Name</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                              placeholder="Aarav Sharma"
                              className="pl-10 h-11"
                              {...field}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Phone */}
                  <FormField
                    control={form.control}
                    name="phone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Phone Number</FormLabel>
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

                  {/* Password + Confirm */}
                  <div className="grid grid-cols-2 gap-3">
                    <FormField
                      control={form.control}
                      name="password"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Password</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                              <Input
                                type={showPassword ? "text" : "password"}
                                placeholder="••••••••"
                                className="pl-10 h-11"
                                {...field}
                              />
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="confirmPassword"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Confirm</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <Input
                                type={showPassword ? "text" : "password"}
                                placeholder="••••••••"
                                className="h-11"
                                {...field}
                              />
                              <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
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
                  </div>

                  {/* State + Language */}
                  <div className="grid grid-cols-2 gap-3">
                    <FormField
                      control={form.control}
                      name="state"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            <MapPin className="inline h-3.5 w-3.5 mr-1" />
                            State
                          </FormLabel>
                          <FormControl>
                            <Combobox
                              items={STATE_ITEMS}
                              value={field.value}
                              onValueChange={field.onChange}
                              placeholder="Select state"
                              searchPlaceholder="Search states…"
                              className="h-11"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="language_preference"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            <Globe className="inline h-3.5 w-3.5 mr-1" />
                            Language
                          </FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            defaultValue={field.value}
                          >
                            <FormControl>
                              <SelectTrigger className="h-11">
                                <SelectValue placeholder="Language" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {LANGUAGES.map((lang) => (
                                <SelectItem key={lang.value} value={lang.value}>
                                  {lang.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* District + Annual Income */}
                  <div className="grid grid-cols-2 gap-3">
                    <FormField
                      control={form.control}
                      name="district"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>District (Optional)</FormLabel>
                          <FormControl>
                            <Combobox
                              items={DISTRICT_ITEMS}
                              value={field.value}
                              onValueChange={field.onChange}
                              placeholder="e.g. Pune, Varanasi"
                              searchPlaceholder="Search districts…"
                              className="h-11"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="annual_income"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            <IndianRupee className="inline h-3.5 w-3.5 mr-1" />
                            Annual Income
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              placeholder="e.g. 120000"
                              className="h-11"
                              inputMode="numeric"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* Consent */}
                  <FormField
                    control={form.control}
                    name="consent_data_processing"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-lg border border-border p-3">
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel className="text-sm">
                            I consent to local data processing
                          </FormLabel>
                          <FormDescription className="text-xs">
                            Your data is processed locally and never leaves your
                            machine. DPDP Act 2023 compliant.
                          </FormDescription>
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={isPending}
                    className="css-btn-primary w-full h-11 text-sm disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
                  >
                    {isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {mode === "full"
                          ? "Setting up your profile..."
                          : "Creating account..."}
                      </>
                    ) : (
                      <>
                        {mode === "full"
                          ? "Create Account & Onboard"
                          : "Create Account"}
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </form>
              </Form>

              <Separator className="my-6" />

              <p className="text-center text-sm text-muted-foreground">
                Already have an account?{" "}
                <Link
                  href="/login"
                  className="css-btn-ghost inline px-0 py-0 font-semibold text-primary"
                >
                  Sign in
                </Link>
              </p>

              <div className="mt-4 rounded-lg bg-muted/50 p-3 text-center">
                <p className="text-xs text-muted-foreground">
                  🔒 Local Mode — No SMS/Email. OTP logged to backend console.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
