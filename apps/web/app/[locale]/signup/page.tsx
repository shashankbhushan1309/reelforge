/** ReelForge AI — Signup Page */
"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useState } from "react";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { useAppStore } from "@/lib/store";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const router = useRouter();
  const setToken = useAppStore((state) => state.setToken);
  const setUser = useAppStore((state) => state.setUser);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    const supabase = createClient();
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: name,
        },
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    if (data.session) {
      setToken(data.session.access_token);
      setUser(data.user);
      router.push("/onboarding");
    } else {
      // Email verification required
      setError("Please check your email to verify your account.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 relative overflow-hidden">
      <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-[var(--color-primary)] rounded-full blur-[128px] opacity-15" />
      <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-[var(--color-accent)] rounded-full blur-[128px] opacity-10" />

      <motion.div
        className="w-full max-w-md glass-card p-8"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Link href="/" className="flex items-center gap-2 mb-8 justify-center">
          <span className="text-2xl">🎬</span>
          <span className="text-xl font-bold gradient-text font-[var(--font-display)]">ReelForge AI</span>
        </Link>

        <h1 className="text-2xl font-bold text-center mb-2">Create your account</h1>
        <p className="text-center text-[var(--color-text-secondary)] mb-6 text-sm">
          Start creating influencer-quality reels in 90 seconds
        </p>

        <div className="grid grid-cols-2 gap-3 mb-6">
          <button className="btn-secondary !py-2.5 flex items-center justify-center gap-2 text-sm">
            <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Google
          </button>
          <button className="btn-secondary !py-2.5 flex items-center justify-center gap-2 text-sm">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12c0-5.523-4.477-10-10-10z"/></svg>
            Apple
          </button>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <div className="h-px flex-1 bg-[var(--color-border)]" />
          <span className="text-xs text-[var(--color-text-muted)]">or</span>
          <div className="h-px flex-1 bg-[var(--color-border)]" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Full name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors text-sm" required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors text-sm" required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min 8 characters" className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors text-sm" required minLength={8} />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full !py-3">
            {loading ? "Creating account..." : "Create Account →"}
          </button>
        </form>

        <p className="text-center text-xs text-[var(--color-text-muted)] mt-4">
          By signing up, you agree to our Terms and Privacy Policy
        </p>
        <p className="text-center text-sm text-[var(--color-text-muted)] mt-4">
          Already have an account?{" "}
          <Link href="/login" className="text-[var(--color-primary-light)] hover:text-white transition-colors">Sign in</Link>
        </p>
      </motion.div>
    </div>
  );
}
