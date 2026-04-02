/** ReelForge AI — Settings Page */
"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useState } from "react";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "@/lib/store";
import { authApi } from "@/lib/api";

const TIERS = [
  { name: "Free", price: "$0", internalName: "free", features: ["3 reels/month", "720p", "Watermark"] },
  { name: "Creator", price: "$12/mo", internalName: "creator", features: ["30 reels/month", "1080p", "No watermark", "Clone Mode"] },
  { name: "Pro", price: "$29/mo", internalName: "pro", features: ["Unlimited reels", "4K", "API access", "50GB vault"] },
  { name: "Studio", price: "$99/mo", internalName: "studio", features: ["Team seats", "White-label", "Priority support"] },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("billing");
  
  const token = useAppStore((s) => s.token);
  const queryClient = useQueryClient();

  const { data: user } = useQuery({
    queryKey: ["user"],
    queryFn: () => authApi.me(token!),
    enabled: !!token,
  });

  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [locale, setLocale] = useState("en");

  // Sync state when user loads
  if (user && !name && user.name) {
    setName(user.name);
    setTimezone(user.timezone || "UTC");
    setLocale(user.locale || "en");
  }

  const updateMutation = useMutation({
    mutationFn: (data: any) => authApi.updateProfile(data, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user"] });
      alert("Settings saved successfully!");
    },
    onError: (err) => {
      alert("Failed to save settings: " + err.message);
    }
  });

  const handleSave = () => {
    updateMutation.mutate({ name, timezone, locale });
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-dark)]">
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[var(--color-bg-dark)]/80 border-b border-[var(--color-border)]">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl">🎬</span>
            <span className="font-bold gradient-text">ReelForge AI</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors">Dashboard</Link>
            <Link href="/vault" className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors">Vault</Link>
            <Link href="/settings" className="text-sm text-white font-medium">Settings</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold font-[var(--font-display)] mb-6">Settings</h1>

        {/* Tabs */}
        <div className="flex gap-1 mb-8 bg-[var(--color-bg-card)] rounded-xl p-1 border border-[var(--color-border)]">
          {["billing", "account", "preferences", "export"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium capitalize transition-all ${
                activeTab === tab ? "gradient-bg text-white" : "text-[var(--color-text-secondary)] hover:text-white"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Billing Tab */}
        {activeTab === "billing" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="glass-card p-6 mb-6">
              <h2 className="text-lg font-semibold mb-1">Current Plan</h2>
              <p className="text-sm text-[var(--color-text-secondary)] mb-4">
                {user?.tier || "Loading..."} · {user?.credits || 0} reels remaining
              </p>
              <div className="flex items-center gap-3">
                <div className="text-3xl font-bold">{user?.credits || 0}</div>
                <div>
                  <p className="text-sm font-medium">Credits Remaining</p>
                  <p className="text-xs text-[var(--color-text-muted)]">Resets monthly</p>
                </div>
              </div>
            </div>

            <h3 className="text-lg font-semibold mb-4">Upgrade Your Plan</h3>
            <div className="grid md:grid-cols-4 gap-4">
              {TIERS.map((tier) => {
                const isCurrent = user?.tier === tier.internalName;
                return (
                <div key={tier.name} className={`glass-card p-5 ${isCurrent ? "border-[var(--color-primary)] border-2" : ""}`}>
                  {isCurrent && <span className="text-xs text-[var(--color-primary-light)] font-semibold">CURRENT</span>}
                  <h4 className="text-lg font-bold mt-1">{tier.name}</h4>
                  <p className="text-xl font-bold mb-3">{tier.price}</p>
                  <ul className="space-y-1 mb-4">
                    {tier.features.map((f) => (
                      <li key={f} className="text-xs text-[var(--color-text-secondary)]">✓ {f}</li>
                    ))}
                  </ul>
                  {!isCurrent && (
                    <button className="btn-primary w-full !text-sm !py-2">Upgrade</button>
                  )}
                </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Account Tab */}
        {activeTab === "account" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="glass-card p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Display Name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white focus:outline-none focus:border-[var(--color-primary)] text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Email</label>
                <input type="email" value={user?.email || ""} className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white focus:outline-none focus:border-[var(--color-primary)] text-sm" disabled />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Timezone</label>
                <select value={timezone} onChange={(e) => setTimezone(e.target.value)} className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white text-sm">
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="Europe/London">Europe/London</option>
                  <option value="Asia/Kolkata">Asia/Kolkata</option>
                  <option value="Asia/Tokyo">Asia/Tokyo</option>
                </select>
              </div>
              <button disabled={updateMutation.isPending} onClick={handleSave} className="btn-primary !text-sm">
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </button>

              <hr className="border-[var(--color-border)] my-6" />

              <div>
                <h3 className="text-sm font-semibold text-[var(--color-error)] mb-2">Danger Zone</h3>
                <p className="text-xs text-[var(--color-text-muted)] mb-3">
                  Permanently delete your account and all data. This cannot be undone.
                </p>
                <button className="px-4 py-2 rounded-xl border border-[var(--color-error)] text-[var(--color-error)] text-sm hover:bg-[var(--color-error)]/10 transition-colors">
                  Delete Account
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Preferences Tab */}
        {activeTab === "preferences" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="glass-card p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium mb-1.5">Default Niche</label>
                <select className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white text-sm">
                  {["Lifestyle", "Travel", "Food", "Fashion", "Fitness", "Tech", "Comedy", "Beauty"].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Region</label>
                <select className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white text-sm">
                  <option value="US">🇺🇸 United States</option>
                  <option value="IN">🇮🇳 India</option>
                  <option value="BR">🇧🇷 Brazil</option>
                  <option value="KR">🇰🇷 South Korea</option>
                  <option value="GB">🇬🇧 United Kingdom</option>
                  <option value="DE">🇩🇪 Germany</option>
                  <option value="JP">🇯🇵 Japan</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Language</label>
                <select value={locale} onChange={(e) => setLocale(e.target.value)} className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white text-sm">
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                </select>
              </div>
              <button disabled={updateMutation.isPending} onClick={handleSave} className="btn-primary !text-sm">
                {updateMutation.isPending ? "Saving..." : "Save Preferences"}
              </button>
            </div>
          </motion.div>
        )}

        {/* Export Tab */}
        {activeTab === "export" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="glass-card p-6 space-y-4">
              <h3 className="text-lg font-semibold">Export Settings</h3>
              <div>
                <label className="block text-sm font-medium mb-1.5">Default Export Format</label>
                <div className="flex gap-3">
                  {["9:16 Portrait", "1:1 Square", "16:9 Landscape"].map((f) => (
                    <button key={f} className="btn-secondary !text-sm flex-1">{f}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Quality</label>
                <select className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-white text-sm">
                  <option>720p (Free)</option>
                  <option>1080p (Creator+)</option>
                  <option>4K (Pro+)</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Include Watermark</p>
                  <p className="text-xs text-[var(--color-text-muted)]">Free tier only</p>
                </div>
                <div className="w-12 h-6 rounded-full bg-[var(--color-primary)] flex items-center px-1">
                  <div className="w-4 h-4 rounded-full bg-white ml-auto" />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
