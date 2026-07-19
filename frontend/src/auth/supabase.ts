import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim() || "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim() || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

// Keep Supabase's OAuth session only for the lifetime of this browser tab.
// This intentionally differs from localStorage persistence: it survives the
// OAuth return and a same-tab reload, but is removed when the tab/session ends.
// The API token provider remains memory-only in lib/api.ts and is cleared on
// sign-out, idle logout, and an identity change.
export const supabaseAuthOptions = {
  autoRefreshToken: true,
  detectSessionInUrl: true,
  persistSession: true,
  storage: window.sessionStorage,
  storageKey: "presidio.supabase.auth.session",
};

export const supabase = createClient(
  supabaseUrl || "https://placeholder.supabase.co",
  supabaseAnonKey || "placeholder",
  { auth: supabaseAuthOptions },
);
