"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Card as NextUICard,
  CardHeader as NextUICardHeader,
  CardBody,
  CardFooter,
  Chip,
  Avatar,
  Divider,
  Progress,
  Skeleton,
} from "@nextui-org/react";
import {
  User,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Shield,
  ShieldCheck,
  Lock,
  KeyRound,
  Save,
  Loader2,
  Globe,
  Fingerprint,
  CreditCard,
} from "lucide-react";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useCurrentUser,
  useUpdateProfile,
  useIdentity,
} from "@/hooks/use-auth";
import { useAppStore } from "@/lib/store";

/**
 * Profile Page — E2/E4/E12: Identity Vault
 * ==========================================
 * Hero UI (NextUI) cards for encrypted vault data.
 * ShadCN forms for profile editing.
 * UIverse verified badge styling.
 *
 * Tabs:
 *   1. Profile Info — editable via PUT /api/v1/auth/profile
 *   2. Identity Vault — read-only decrypted fields from GET /api/v1/identity/{token}
 *   3. Security — verification status (stubbed as "Verified")
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

const profileSchema = z.object({
  name: z.string().min(2).optional(),
  email: z.string().email().optional().or(z.literal("")),
  date_of_birth: z.string().optional(),
  gender: z.string().optional(),
  state: z.string().optional(),
  district: z.string().optional(),
  pincode: z.string().optional(),
  language_preference: z.string().optional(),
});

type ProfileFormData = z.infer<typeof profileSchema>;

// ── Profile Completeness Calculator ─────────────────────────────────────────

function computeCompleteness(user: Record<string, unknown> | null): number {
  if (!user) return 0;
  const fields = [
    "name", "phone", "email", "date_of_birth", "gender",
    "state", "district", "pincode", "language_preference",
  ];
  const filled = fields.filter((f) => user[f] && String(user[f]).length > 0);
  return Math.round((filled.length / fields.length) * 100);
}

export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState("profile");
  const { data: currentUser, isLoading: userLoading } = useCurrentUser();
  const updateProfile = useUpdateProfile();
  const storeUser = useAppStore((s) => s.user);
  const identityToken = storeUser?.identity_token;
  const { data: identity, isLoading: identityLoading } =
    useIdentity(identityToken);

  const completeness = computeCompleteness(
    currentUser as unknown as Record<string, unknown>
  );

  const form = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    values: {
      name: currentUser?.name || "",
      email: currentUser?.email || "",
      date_of_birth: currentUser?.date_of_birth || "",
      gender: currentUser?.gender || "",
      state: currentUser?.state || "",
      district: currentUser?.district || "",
      pincode: currentUser?.pincode || "",
      language_preference: currentUser?.language_preference || "en",
    },
  });

  function onSubmit(data: ProfileFormData) {
    // Filter out empty strings
    const filtered = Object.fromEntries(
      Object.entries(data).filter(([, v]) => v && String(v).length > 0)
    );
    updateProfile.mutate(filtered);
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">My Profile</h2>
        <p className="text-muted-foreground">
          Your identity vault and personal information
        </p>
      </div>

      {/* Top Summary Card — Hero UI */}
      <NextUICard className="shadow-lg">
        <NextUICardHeader className="flex gap-4 p-6">
          <Avatar
            name={currentUser?.name || storeUser?.name || "U"}
            size="lg"
            className="h-16 w-16 text-lg"
            color="primary"
          />
          <div className="flex flex-col flex-1">
            <div className="flex items-center gap-2">
              {userLoading ? (
                <Skeleton className="h-6 w-40 rounded-lg" />
              ) : (
                <h3 className="text-xl font-semibold">
                  {currentUser?.name || storeUser?.name || "User"}
                </h3>
              )}
              {/* Stubbed as always Verified per constraint */}
              <span className="verified-badge">
                <ShieldCheck className="h-3 w-3" />
                Verified
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              {currentUser?.phone || storeUser?.phone || "Phone not set"}
            </p>
            {currentUser?.roles?.length ? (
              <div className="flex gap-1 mt-1">
                {currentUser.roles.map((role) => (
                  <Chip key={role} size="sm" variant="flat" color="primary">
                    {role}
                  </Chip>
                ))}
              </div>
            ) : null}
          </div>
        </NextUICardHeader>
        <Divider />
        <CardBody className="px-6 py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Profile Completeness</span>
            <span className="text-sm font-semibold">{completeness}%</span>
          </div>
          <Progress
            value={completeness}
            color={completeness >= 80 ? "success" : completeness >= 50 ? "warning" : "danger"}
            size="sm"
            className="max-w-full"
            aria-label="Profile completeness"
          />
        </CardBody>
      </NextUICard>

      {/* Tabbed Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="profile">
            <User className="h-4 w-4 mr-1.5" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="vault">
            <Lock className="h-4 w-4 mr-1.5" />
            Identity Vault
          </TabsTrigger>
          <TabsTrigger value="security">
            <Shield className="h-4 w-4 mr-1.5" />
            Security
          </TabsTrigger>
        </TabsList>

        {/* ── Tab 1: Profile Info ──────────────────────────────────────── */}
        <TabsContent value="profile" className="space-y-4 mt-4">
          <NextUICard className="shadow-md">
            <CardBody className="p-6">
              <h4 className="text-lg font-semibold mb-4">
                Personal Information
              </h4>
              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit(onSubmit)}
                  className="space-y-4"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            <User className="inline h-3.5 w-3.5 mr-1" />
                            Full Name
                          </FormLabel>
                          <FormControl>
                            <Input className="h-11" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            <Mail className="inline h-3.5 w-3.5 mr-1" />
                            Email
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="email"
                              placeholder="you@example.com"
                              className="h-11"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="date_of_birth"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            <Calendar className="inline h-3.5 w-3.5 mr-1" />
                            Date of Birth
                          </FormLabel>
                          <FormControl>
                            <Input type="date" className="h-11" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="gender"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Gender</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            value={field.value}
                          >
                            <FormControl>
                              <SelectTrigger className="h-11">
                                <SelectValue placeholder="Select gender" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="male">Male</SelectItem>
                              <SelectItem value="female">Female</SelectItem>
                              <SelectItem value="other">Other</SelectItem>
                              <SelectItem value="prefer_not_to_say">
                                Prefer not to say
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="state"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            <MapPin className="inline h-3.5 w-3.5 mr-1" />
                            State
                          </FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            value={field.value}
                          >
                            <FormControl>
                              <SelectTrigger className="h-11">
                                <SelectValue placeholder="Select state" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {INDIAN_STATES.map((s) => (
                                <SelectItem key={s} value={s}>
                                  {s}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="district"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>District</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="e.g. Pune"
                              className="h-11"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="pincode"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Pincode</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="411001"
                              maxLength={6}
                              className="h-11"
                              {...field}
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
                            value={field.value}
                          >
                            <FormControl>
                              <SelectTrigger className="h-11">
                                <SelectValue placeholder="Select language" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="en">English</SelectItem>
                              <SelectItem value="hi">Hindi</SelectItem>
                              <SelectItem value="bn">Bengali</SelectItem>
                              <SelectItem value="te">Telugu</SelectItem>
                              <SelectItem value="mr">Marathi</SelectItem>
                              <SelectItem value="ta">Tamil</SelectItem>
                              <SelectItem value="gu">Gujarati</SelectItem>
                              <SelectItem value="kn">Kannada</SelectItem>
                              <SelectItem value="ml">Malayalam</SelectItem>
                              <SelectItem value="pa">Punjabi</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <Separator className="my-4" />

                  <button
                    type="submit"
                    disabled={updateProfile.isPending}
                    className="css-btn-primary h-11 text-sm disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
                  >
                    {updateProfile.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        Save Changes
                      </>
                    )}
                  </button>
                </form>
              </Form>
            </CardBody>
          </NextUICard>
        </TabsContent>

        {/* ── Tab 2: Identity Vault ────────────────────────────────────── */}
        <TabsContent value="vault" className="space-y-4 mt-4">
          <NextUICard className="shadow-md">
            <NextUICardHeader className="p-6 pb-2">
              <div className="flex items-center gap-2">
                <Lock className="h-5 w-5 text-primary" />
                <h4 className="text-lg font-semibold">
                  Encrypted Identity Vault
                </h4>
              </div>
            </NextUICardHeader>
            <Divider />
            <CardBody className="p-6">
              {!identityToken ? (
                <div className="text-center py-8">
                  <KeyRound className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
                  <p className="text-muted-foreground">
                    No identity vault found. Use &quot;Full Onboard&quot; to create one,
                    or it will be created when the backend is running.
                  </p>
                </div>
              ) : identityLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <Skeleton className="h-10 w-10 rounded-lg" />
                      <div className="space-y-1.5 flex-1">
                        <Skeleton className="h-3 w-20 rounded" />
                        <Skeleton className="h-4 w-48 rounded" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : identity ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <VaultField
                    icon={<Fingerprint className="h-4 w-4" />}
                    label="Identity Token"
                    value={identity.identity_token}
                    masked
                  />
                  <VaultField
                    icon={<User className="h-4 w-4" />}
                    label="Name"
                    value={identity.name}
                  />
                  <VaultField
                    icon={<Phone className="h-4 w-4" />}
                    label="Phone"
                    value={identity.phone}
                  />
                  <VaultField
                    icon={<Mail className="h-4 w-4" />}
                    label="Email"
                    value={identity.email}
                  />
                  <VaultField
                    icon={<MapPin className="h-4 w-4" />}
                    label="Address"
                    value={identity.address}
                  />
                  <VaultField
                    icon={<Calendar className="h-4 w-4" />}
                    label="Date of Birth"
                    value={identity.dob}
                  />
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-4">
                  Failed to load identity vault data.
                </p>
              )}

              <div className="mt-6 rounded-lg bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">
                  🔐 AES-256 encrypted at rest. Decrypted on-demand via Identity
                  Engine (E2). No data leaves your local machine.
                </p>
              </div>
            </CardBody>
          </NextUICard>
        </TabsContent>

        {/* ── Tab 3: Security ──────────────────────────────────────────── */}
        <TabsContent value="security" className="space-y-4 mt-4">
          <NextUICard className="shadow-md">
            <CardBody className="p-6">
              <h4 className="text-lg font-semibold mb-4">
                Verification Status
              </h4>
              <div className="space-y-4">
                <SecurityItem
                  icon={<Phone className="h-5 w-5" />}
                  title="Phone Verification"
                  description="Mobile number verified via local OTP"
                  status="verified"
                />
                <SecurityItem
                  icon={<Fingerprint className="h-5 w-5" />}
                  title="Identity Verification"
                  description="Stubbed as verified (local mode)"
                  status="verified"
                />
                <SecurityItem
                  icon={<CreditCard className="h-5 w-5" />}
                  title="Document Verification"
                  description="No DigiLocker integration (local mode)"
                  status="stubbed"
                />
                <SecurityItem
                  icon={<Shield className="h-5 w-5" />}
                  title="Data Encryption"
                  description="AES-256 encryption active for vault data"
                  status="verified"
                />
              </div>

              <div className="mt-6 rounded-lg bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">
                  🔒 Local Mode — Identity verification is stubbed. In
                  production, this would connect to DigiLocker and Aadhaar APIs.
                </p>
              </div>
            </CardBody>
          </NextUICard>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ── Sub-Components ───────────────────────────────────────────────────────────

function VaultField({
  icon,
  label,
  value,
  masked = false,
}: {
  icon: React.ReactNode;
  label: string;
  value?: string;
  masked?: boolean;
}) {
  const [revealed, setRevealed] = useState(false);
  const display = !value
    ? "—"
    : masked && !revealed
      ? `${value.slice(0, 8)}${"•".repeat(Math.max(0, value.length - 8))}`
      : value;

  return (
    <NextUICard className="shadow-sm border border-border">
      <CardBody className="flex flex-row items-center gap-3 p-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-sm font-medium truncate">{display}</p>
        </div>
        {masked && value && (
          <button
            onClick={() => setRevealed(!revealed)}
            className="text-xs text-primary hover:underline shrink-0"
          >
            {revealed ? "Hide" : "Reveal"}
          </button>
        )}
      </CardBody>
    </NextUICard>
  );
}

function SecurityItem({
  icon,
  title,
  description,
  status,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  status: "verified" | "stubbed" | "pending";
}) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-border p-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
        {icon}
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      {status === "verified" ? (
        <span className="verified-badge">
          <ShieldCheck className="h-3 w-3" />
          Verified
        </span>
      ) : status === "stubbed" ? (
        <Chip size="sm" variant="flat" color="warning">
          Stubbed
        </Chip>
      ) : (
        <Chip size="sm" variant="flat" color="default">
          Pending
        </Chip>
      )}
    </div>
  );
}
