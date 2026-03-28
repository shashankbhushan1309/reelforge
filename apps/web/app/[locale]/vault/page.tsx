/** ReelForge AI — Media Vault */
"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useState } from "react";

const MOCK_MEDIA = [
  { id: "1", type: "video", filename: "beach_sunset.mp4", duration_ms: 12000, size_bytes: 4200000, score: 87, mood: "calm", status: "ready" },
  { id: "2", type: "photo", filename: "portrait_golden.jpg", duration_ms: null, size_bytes: 2100000, score: 92, mood: "joyful", status: "ready" },
  { id: "3", type: "video", filename: "city_walk.mp4", duration_ms: 18000, size_bytes: 6800000, score: 78, mood: "energetic", status: "ready" },
  { id: "4", type: "video", filename: "cooking_clip.mp4", duration_ms: 25000, size_bytes: 9200000, score: 85, mood: "calm", status: "ready" },
  { id: "5", type: "photo", filename: "mountain_view.jpg", duration_ms: null, size_bytes: 3500000, score: 95, mood: "dramatic", status: "ready" },
  { id: "6", type: "video", filename: "dance_routine.mp4", duration_ms: 30000, size_bytes: 12000000, score: 71, mood: "energetic", status: "ready" },
  { id: "7", type: "photo", filename: "food_overhead.jpg", duration_ms: null, size_bytes: 1800000, score: 88, mood: "joyful", status: "ready" },
  { id: "8", type: "video", filename: "travel_montage.mp4", duration_ms: 45000, size_bytes: 18000000, score: 82, mood: "powerful", status: "ready" },
];

function ScoreDot({ score }: { score: number }) {
  const color = score >= 85 ? "var(--color-success)" : score >= 70 ? "var(--color-warning)" : "var(--color-error)";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-xs text-[var(--color-text-muted)]">{score}</span>
    </div>
  );
}

export default function VaultPage() {
  const [filter, setFilter] = useState<"all" | "video" | "photo">("all");
  const [sort, setSort] = useState("score");

  const filtered = MOCK_MEDIA
    .filter((m) => filter === "all" || m.type === filter)
    .sort((a, b) => sort === "score" ? b.score - a.score : b.size_bytes - a.size_bytes);

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
            <Link href="/vault" className="text-sm text-white font-medium">Vault</Link>
            <Link href="/settings" className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors">Settings</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold font-[var(--font-display)]">Media Vault</h1>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {MOCK_MEDIA.length} items · Scored & analysed
            </p>
          </div>
          <Link href="/dashboard" className="btn-primary !text-sm !py-2">
            + Create Reel
          </Link>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex gap-2">
            {(["all", "video", "photo"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm transition-all ${
                  filter === f ? "gradient-bg text-white" : "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] border border-[var(--color-border)]"
                }`}
              >
                {f === "all" ? "All" : f === "video" ? "🎬 Videos" : "📷 Photos"}
              </button>
            ))}
          </div>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="px-3 py-2 rounded-lg text-sm bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-[var(--color-text-secondary)]"
          >
            <option value="score">Sort by Score</option>
            <option value="size">Sort by Size</option>
          </select>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filtered.map((item, i) => (
            <motion.div
              key={item.id}
              className="glass-card overflow-hidden group cursor-pointer"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <div className="aspect-square bg-[var(--color-bg-elevated)] flex items-center justify-center relative">
                <span className="text-4xl">{item.type === "video" ? "🎬" : "📷"}</span>
                {item.duration_ms && (
                  <span className="absolute bottom-2 right-2 text-xs bg-black/60 px-2 py-0.5 rounded">
                    {Math.round(item.duration_ms / 1000)}s
                  </span>
                )}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <span className="text-white text-sm font-medium">View Details</span>
                </div>
              </div>
              <div className="p-3">
                <p className="text-sm font-medium truncate">{item.filename}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {(item.size_bytes / 1024 / 1024).toFixed(1)} MB
                  </span>
                  <ScoreDot score={item.score} />
                </div>
                <span className="inline-block mt-1.5 text-xs px-2 py-0.5 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
                  {item.mood}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
