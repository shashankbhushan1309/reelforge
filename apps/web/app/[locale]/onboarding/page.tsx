/** ReelForge AI — Onboarding Page */
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import Link from "next/link";

const NICHES = [
  { name: "Travel", emoji: "✈️" },
  { name: "Food", emoji: "🍽️" },
  { name: "Fashion", emoji: "👗" },
  { name: "Fitness", emoji: "💪" },
  { name: "Lifestyle", emoji: "🌟" },
  { name: "Tech", emoji: "💻" },
  { name: "Comedy", emoji: "😂" },
  { name: "Beauty", emoji: "💄" },
  { name: "Music", emoji: "🎵" },
  { name: "Photography", emoji: "📸" },
  { name: "Gaming", emoji: "🎮" },
  { name: "Education", emoji: "📚" },
];

const REGIONS = [
  { code: "US", name: "United States", flag: "🇺🇸" },
  { code: "IN", name: "India", flag: "🇮🇳" },
  { code: "BR", name: "Brazil", flag: "🇧🇷" },
  { code: "KR", name: "South Korea", flag: "🇰🇷" },
  { code: "GB", name: "United Kingdom", flag: "🇬🇧" },
  { code: "DE", name: "Germany", flag: "🇩🇪" },
  { code: "JP", name: "Japan", flag: "🇯🇵" },
  { code: "ID", name: "Indonesia", flag: "🇮🇩" },
];

import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [selectedNiches, setSelectedNiches] = useState<string[]>([]);
  const [selectedRegion, setSelectedRegion] = useState("US");
  
  const router = useRouter();
  const setNiche = useAppStore((s) => s.setNiche);
  const setRegion = useAppStore((s) => s.setRegion);

  const toggleNiche = (niche: string) => {
    setSelectedNiches((prev) =>
      prev.includes(niche) ? prev.filter((n) => n !== niche) : [...prev, niche]
    );
  };

  const handleComplete = () => {
    if (selectedNiches.length > 0) {
      setNiche(selectedNiches[0]);
    }
    setRegion(selectedRegion);
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 relative overflow-hidden">
      <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-[var(--color-primary)] rounded-full blur-[128px] opacity-10" />
      <div className="absolute bottom-1/3 right-1/3 w-96 h-96 bg-[var(--color-accent)] rounded-full blur-[128px] opacity-10" />

      <motion.div className="w-full max-w-xl glass-card p-8" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        {/* Progress */}
        <div className="flex gap-1 mb-8">
          {[0, 1, 2].map((s) => (
            <div key={s} className={`h-1 flex-1 rounded-full transition-all ${s <= step ? "gradient-bg" : "bg-[var(--color-bg-elevated)]"}`} />
          ))}
        </div>

        <AnimatePresence mode="wait">
          {step === 0 && (
            <motion.div key="welcome" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h1 className="text-3xl font-bold mb-3 font-[var(--font-display)]">Welcome to ReelForge! 🎬</h1>
              <p className="text-[var(--color-text-secondary)] mb-8">
                Let's personalize your experience. This takes 30 seconds.
              </p>
              <button onClick={() => setStep(1)} className="btn-primary w-full">Let's Go →</button>
            </motion.div>
          )}

          {step === 1 && (
            <motion.div key="niche" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h2 className="text-2xl font-bold mb-2 font-[var(--font-display)]">What do you create?</h2>
              <p className="text-sm text-[var(--color-text-secondary)] mb-6">Pick your niches. This helps us find the right trends for you.</p>
              <div className="grid grid-cols-3 gap-3 mb-6">
                {NICHES.map((n) => (
                  <button key={n.name} onClick={() => toggleNiche(n.name)} className={`p-3 rounded-xl text-sm transition-all ${selectedNiches.includes(n.name) ? "gradient-bg text-white font-medium" : "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] border border-[var(--color-border)]"}`}>
                    <span className="text-xl block mb-1">{n.emoji}</span>
                    {n.name}
                  </button>
                ))}
              </div>
              <button onClick={() => setStep(2)} disabled={selectedNiches.length === 0} className="btn-primary w-full">Continue →</button>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div key="region" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h2 className="text-2xl font-bold mb-2 font-[var(--font-display)]">Where are you based?</h2>
              <p className="text-sm text-[var(--color-text-secondary)] mb-6">We'll show you trends from your region.</p>
              <div className="grid grid-cols-2 gap-3 mb-6">
                {REGIONS.map((r) => (
                  <button key={r.code} onClick={() => setSelectedRegion(r.code)} className={`p-3 rounded-xl text-sm text-left flex items-center gap-3 transition-all ${selectedRegion === r.code ? "gradient-bg text-white font-medium" : "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] border border-[var(--color-border)]"}`}>
                    <span className="text-xl">{r.flag}</span>
                    {r.name}
                  </button>
                ))}
              </div>
              <button onClick={handleComplete} className="btn-primary w-full block text-center">
                Start Creating ✨
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
