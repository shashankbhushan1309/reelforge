/** ReelForge AI — Landing Page */
"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const FEATURES = [
  {
    icon: "🎬",
    title: "Smart Media Decomposition",
    description: "AI breaks your raw footage into perfect, usable segments. No trimming needed.",
  },
  {
    icon: "🧬",
    title: "Style DNA Extraction",
    description: "Clone any reel's style — pace, color grade, transitions, text energy, BPM.",
  },
  {
    icon: "📐",
    title: "Reel Blueprint Mapping",
    description: "AI generates time-coded slot structures mapped to trending reel formats.",
  },
  {
    icon: "✨",
    title: "Auto-Edit Layer",
    description: "Beat-sync cuts, speed ramps, colour grading, transitions, and text overlays — all automated.",
  },
  {
    icon: "📊",
    title: "Trend Pulse Engine",
    description: "Continuously updated trend intelligence powering every creative decision.",
  },
  {
    icon: "🎯",
    title: "Shot Director",
    description: "Get precise shot-by-shot instructions to film content that matches any style.",
  },
];

const PRICING = [
  {
    tier: "Free",
    price: "$0",
    period: "",
    features: ["3 reels/month", "720p export", "Auto-Create only", "Watermark"],
    cta: "Get Started",
    highlighted: false,
  },
  {
    tier: "Creator",
    price: "$12",
    period: "/mo",
    features: ["30 reels/month", "1080p export", "Clone + Auto-Create", "5GB vault", "Trend Pulse", "No watermark"],
    cta: "Start Creating",
    highlighted: true,
  },
  {
    tier: "Pro",
    price: "$29",
    period: "/mo",
    features: ["Unlimited reels", "4K export", "Brand Memory", "Multi-platform export", "API access", "50GB vault"],
    cta: "Go Pro",
    highlighted: false,
  },
  {
    tier: "Studio",
    price: "$99",
    period: "/mo",
    features: ["Everything in Pro", "5 team seats", "White-label exports", "Custom DNA templates", "Webhook API", "Priority support"],
    cta: "Contact Sales",
    highlighted: false,
  },
];

const fadeInUp = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6 },
};

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* ── Navbar ── */}
      <nav className="fixed top-0 w-full z-50 backdrop-blur-xl bg-[var(--color-bg-dark)]/80 border-b border-[var(--color-border)]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">🎬</span>
            <span className="text-xl font-bold gradient-text font-[var(--font-display)]">
              ReelForge AI
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors">
              Features
            </a>
            <a href="#pricing" className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors">
              Pricing
            </a>
            <Link href="/login" className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors">
              Log in
            </Link>
            <Link href="/signup" className="btn-primary text-sm !py-2 !px-5">
              Start Free →
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Background gradient orbs */}
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-[var(--color-primary)] rounded-full blur-[128px] opacity-20" />
        <div className="absolute top-40 right-1/4 w-96 h-96 bg-[var(--color-secondary)] rounded-full blur-[128px] opacity-15" />
        <div className="absolute bottom-0 left-1/2 w-96 h-96 bg-[var(--color-accent)] rounded-full blur-[128px] opacity-10" />

        <div className="max-w-5xl mx-auto text-center relative z-10">
          <motion.div {...fadeInUp}>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-glass)] mb-8 text-sm text-[var(--color-text-secondary)]">
              <span className="w-2 h-2 rounded-full bg-[var(--color-success)] animate-pulse" />
              World&apos;s first zero-edit AI video director
            </div>
          </motion.div>

          <motion.h1
            className="text-5xl md:text-7xl font-bold leading-tight mb-6 font-[var(--font-display)]"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
          >
            Upload raw footage.
            <br />
            <span className="gradient-text">Get influencer reels.</span>
          </motion.h1>

          <motion.p
            className="text-lg md:text-xl text-[var(--color-text-secondary)] max-w-2xl mx-auto mb-10"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            ReelForge AI does everything a professional editor spends 2-4 hours doing — in under 90 seconds.
            Beat-synced cuts, colour grading, transitions, captions, all trend-aware.
          </motion.p>

          <motion.div
            className="flex flex-col sm:flex-row gap-4 justify-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Link href="/signup" className="btn-primary text-lg !py-4 !px-10">
              Start Creating for Free →
            </Link>
            <a href="#features" className="btn-secondary text-lg !py-4 !px-10">
              See How It Works
            </a>
          </motion.div>

          <motion.p
            className="mt-6 text-sm text-[var(--color-text-muted)]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            No credit card required · 3 free reels · Export-ready for Instagram, TikTok, YouTube Shorts
          </motion.p>
        </div>
      </section>

      {/* ── Two Modes ── */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4 font-[var(--font-display)]">
            Two Modes. One Platform.
          </h2>
          <p className="text-center text-[var(--color-text-secondary)] mb-12 max-w-2xl mx-auto">
            Whether you want to clone a trending reel&apos;s style or let AI create from scratch — ReelForge handles it all.
          </p>

          <div className="grid md:grid-cols-2 gap-6">
            <motion.div
              className="glass-card p-8"
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl gradient-bg flex items-center justify-center text-2xl">🧬</div>
                <h3 className="text-2xl font-bold">Clone Mode</h3>
              </div>
              <p className="text-[var(--color-text-secondary)] leading-relaxed">
                Upload an inspiration reel. AI extracts the Style DNA — pace, colour grade, transition type,
                text energy, BPM. Then generates a precise shot list. You film it. AI recreates the same style
                with your content.
              </p>
            </motion.div>

            <motion.div
              className="glass-card p-8"
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-primary)] flex items-center justify-center text-2xl">⚡</div>
                <h3 className="text-2xl font-bold">Auto-Create Mode</h3>
              </div>
              <p className="text-[var(--color-text-secondary)] leading-relaxed">
                Dump raw, unedited footage and photos. AI analyses everything, scores every moment, picks the
                best clips, maps them to a trending reel structure, and produces a finished reel with edits,
                transitions, music sync, captions, and colour grade.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="py-20 px-6 bg-[var(--color-bg-card)]">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4 font-[var(--font-display)]">
            <span className="gradient-text">Core Features</span>
          </h2>
          <p className="text-center text-[var(--color-text-secondary)] mb-12 max-w-2xl mx-auto">
            Every feature built to produce influencer-grade output, every single time.
          </p>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature, i) => (
              <motion.div
                key={feature.title}
                className="glass-card p-6"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
              >
                <div className="text-3xl mb-4">{feature.icon}</div>
                <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 font-[var(--font-display)]">
            How It Works
          </h2>

          <div className="space-y-8">
            {[
              { step: "01", title: "Upload", desc: "Drop your raw videos and photos. Any format, any length. No pre-editing needed." },
              { step: "02", title: "AI Analyses", desc: "Scene detection, frame scoring, audio analysis, beat mapping — all in seconds." },
              { step: "03", title: "Blueprint Generated", desc: "AI creates a time-coded reel structure matched to trending patterns." },
              { step: "04", title: "Reel Assembled", desc: "Beat-synced cuts, transitions, colour grade, text overlays, audio mix — all automated." },
              { step: "05", title: "Download & Share", desc: "Export-ready for Instagram, TikTok, YouTube Shorts. One tap to share." },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                className="flex gap-6 items-start"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
              >
                <div className="w-12 h-12 rounded-xl gradient-bg flex items-center justify-center text-sm font-bold shrink-0">
                  {item.step}
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-1">{item.title}</h3>
                  <p className="text-[var(--color-text-secondary)]">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="py-20 px-6 bg-[var(--color-bg-card)]">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4 font-[var(--font-display)]">
            Simple, Transparent Pricing
          </h2>
          <p className="text-center text-[var(--color-text-secondary)] mb-12">
            Start free. Upgrade when you&apos;re ready to go viral.
          </p>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {PRICING.map((plan) => (
              <motion.div
                key={plan.tier}
                className={`rounded-2xl p-6 ${
                  plan.highlighted
                    ? "bg-gradient-to-b from-[var(--color-primary)]/20 to-[var(--color-bg-card)] border-2 border-[var(--color-primary)] glow-primary"
                    : "glass-card"
                }`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                {plan.highlighted && (
                  <div className="text-xs font-semibold text-[var(--color-primary-light)] mb-2">
                    MOST POPULAR
                  </div>
                )}
                <h3 className="text-xl font-bold mb-1">{plan.tier}</h3>
                <div className="flex items-baseline gap-1 mb-4">
                  <span className="text-3xl font-bold">{plan.price}</span>
                  <span className="text-sm text-[var(--color-text-muted)]">{plan.period}</span>
                </div>
                <ul className="space-y-2 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="text-sm text-[var(--color-text-secondary)] flex items-center gap-2">
                      <span className="text-[var(--color-success)]">✓</span> {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/signup"
                  className={`block text-center rounded-xl py-2.5 text-sm font-semibold transition-all ${
                    plan.highlighted
                      ? "btn-primary w-full"
                      : "btn-secondary w-full"
                  }`}
                >
                  {plan.cta}
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-12 px-6 border-t border-[var(--color-border)]">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-xl">🎬</span>
            <span className="font-bold gradient-text">ReelForge AI</span>
          </div>
          <div className="flex gap-6 text-sm text-[var(--color-text-muted)]">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">Support</a>
            <a href="#" className="hover:text-white transition-colors">API Docs</a>
          </div>
          <p className="text-sm text-[var(--color-text-muted)]">
            © 2025 ReelForge AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
