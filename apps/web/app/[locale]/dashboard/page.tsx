/** ReelForge AI — Dashboard: Main creation hub */
"use client";

import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { uploadApi, jobsApi, reelsApi } from "@/lib/api";
import { DNAVisualizer } from "@/components/editor/DNAVisualizer";
import { ShotDirector } from "@/components/editor/ShotDirector";
import { ReelPlayer } from "@/components/reel/ReelPlayer";

const NICHES = [
  "Travel", "Food", "Fashion", "Fitness", "Lifestyle",
  "Tech", "Comedy", "Beauty", "Music", "Photography",
];

const STAGES = [
  { key: "queued", label: "Queued", icon: "⏳" },
  { key: "ingesting", label: "Ingesting", icon: "📥" },
  { key: "analysing", label: "Analysing", icon: "🔍" },
  { key: "extracting_dna", label: "Extracting DNA", icon: "🧬" },
  { key: "generating_blueprint", label: "Blueprint", icon: "📐" },
  { key: "assembling", label: "Assembling", icon: "🎬" },
  { key: "completed", label: "Complete", icon: "✅" },
];

export default function DashboardPage() {
  const { mode, setMode } = useAppStore();
  const [files, setFiles] = useState<File[]>([]);
  const [inspirationFile, setInspirationFile] = useState<File | null>(null);
  const [niche, setNiche] = useState("Lifestyle");
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [reelReady, setReelReady] = useState(false);
  
  const token = useAppStore((s) => s.token);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobData, setJobData] = useState<any>(null);
  const [reelData, setReelData] = useState<any>(null);

  // Poll for job updates
  useEffect(() => {
    if (!activeJobId || !isGenerating) return;

    const interval = setInterval(async () => {
      try {
        const job = await jobsApi.get(activeJobId, token!);
        setJobData(job);
        setCurrentStage(job.status);
        setProgress(job.progress);

        if (job.status === "completed") {
          setIsGenerating(false);
          setReelReady(true);
          setActiveJobId(null);
          if (job.reel_id) {
             const reel = await reelsApi.get(job.reel_id, token!);
             setReelData(reel);
          }
        } else if (job.status === "failed") {
          setIsGenerating(false);
          setActiveJobId(null);
          alert("Job failed. Please try again.");
        }
      } catch (err) {
        console.error("Failed to poll job", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeJobId, isGenerating, token]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...droppedFiles]);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const handleInspirationSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setInspirationFile(e.target.files[0]);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const startGeneration = async () => {
    if (!token) return alert("You must be logged in to create a reel");
    if (files.length === 0) return alert("Please upload media first");
    if (mode === "clone" && !inspirationFile) return alert("Please upload an inspiration file");

    setIsGenerating(true);
    setReelReady(false);
    setProgress(0);
    setCurrentStage("queued");

    try {
      // 1. Upload files
      const mediaIds = [];
      for (const file of files) {
        const res = await uploadApi.direct(file, token);
        mediaIds.push(res.media_id);
      }

      // 2. Upload inspiration if cloning
      let inspirationMediaId = null;
      if (mode === "clone" && inspirationFile) {
        const res = await uploadApi.direct(inspirationFile, token);
        inspirationMediaId = res.media_id;
      }

      // 3. Create job
      let jobRes;
      if (mode === "clone") {
        jobRes = await jobsApi.createClone(
          { inspiration_media_id: inspirationMediaId!, user_media_ids: mediaIds },
          token
        );
      } else {
        jobRes = await jobsApi.createAuto(
          { media_ids: mediaIds, niche, region: "US" }, // Passing generic US for now, region usually comes from store
          token
        );
      }

      setActiveJobId(jobRes.id);
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to start generation");
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-dark)]">
      {/* ── Top Nav ── */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[var(--color-bg-dark)]/80 border-b border-[var(--color-border)]">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl">🎬</span>
            <span className="font-bold gradient-text">ReelForge AI</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/vault" className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors">
              Vault
            </Link>
            <Link href="/settings" className="text-sm text-[var(--color-text-secondary)] hover:text-white transition-colors">
              Settings
            </Link>
            <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center text-xs font-bold">
              U
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* ── Mode Toggle ── */}
        <div className="flex items-center justify-center mb-8">
          <div className="inline-flex rounded-xl p-1 bg-[var(--color-bg-card)] border border-[var(--color-border)]">
            <button
              onClick={() => setMode("auto")}
              className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
                mode === "auto"
                  ? "bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-secondary)] text-white shadow-lg"
                  : "text-[var(--color-text-secondary)] hover:text-white"
              }`}
            >
              ⚡ Auto-Create
            </button>
            <button
              onClick={() => setMode("clone")}
              className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
                mode === "clone"
                  ? "bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-secondary)] text-white shadow-lg"
                  : "text-[var(--color-text-secondary)] hover:text-white"
              }`}
            >
              🧬 Clone Mode
            </button>
          </div>
        </div>

        {/* ── Clone Mode: Inspiration Upload ── */}
        <AnimatePresence mode="wait">
          {mode === "clone" && (
            <motion.div
              key="clone-inspiration"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6"
            >
              <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">
                Step 1: Upload Inspiration Reel
              </h3>
              <div className="glass-card p-6">
                {inspirationFile ? (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg gradient-bg flex items-center justify-center">🧬</div>
                      <div>
                        <p className="text-sm font-medium">{inspirationFile.name}</p>
                        <p className="text-xs text-[var(--color-text-muted)]">
                          {(inspirationFile.size / 1024 / 1024).toFixed(1)} MB
                        </p>
                      </div>
                    </div>
                    <button onClick={() => setInspirationFile(null)} className="text-xs text-[var(--color-error)] hover:underline">
                      Remove
                    </button>
                  </div>
                ) : (
                  <label className="dropzone block cursor-pointer !p-8">
                    <input type="file" accept="video/*" onChange={handleInspirationSelect} className="hidden" />
                    <p className="text-lg mb-1">🎥 Drop an inspiration reel here</p>
                    <p className="text-sm text-[var(--color-text-muted)]">
                      AI will extract the Style DNA — pace, colour grade, transitions
                    </p>
                  </label>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Upload Zone ── */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">
            {mode === "clone" ? "Step 2: Upload Your Media" : "Upload Raw Media"}
          </h3>
          <div
            className="dropzone"
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            <label className="cursor-pointer block">
              <input
                type="file"
                accept="video/*,image/*"
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
              <div className="text-4xl mb-3">📁</div>
              <p className="text-lg mb-1">Drop videos & photos here</p>
              <p className="text-sm text-[var(--color-text-muted)]">
                MP4, MOV, JPG, PNG, WEBP — any raw, unedited footage
              </p>
            </label>
          </div>
        </div>

        {/* ── Uploaded Files Grid ── */}
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-6"
          >
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">
              Uploaded ({files.length} files)
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {files.map((file, i) => (
                <div key={i} className="glass-card p-3 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[var(--color-bg-elevated)] flex items-center justify-center text-lg shrink-0">
                    {file.type.startsWith("video") ? "🎬" : "📷"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium truncate">{file.name}</p>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      {(file.size / 1024 / 1024).toFixed(1)} MB
                    </p>
                  </div>
                  <button
                    onClick={() => removeFile(i)}
                    className="text-[var(--color-text-muted)] hover:text-[var(--color-error)] text-lg"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* ── Niche & Options ── */}
        {mode === "auto" && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">Content Niche</h3>
            <div className="flex flex-wrap gap-2">
              {NICHES.map((n) => (
                <button
                  key={n}
                  onClick={() => setNiche(n)}
                  className={`px-4 py-2 rounded-xl text-sm transition-all ${
                    niche === n
                      ? "gradient-bg text-white font-medium"
                      : "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] border border-[var(--color-border)] hover:border-[var(--color-border-hover)]"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Generate Button ── */}
        {files.length > 0 && !isGenerating && !reelReady && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <button
              onClick={startGeneration}
              className="btn-primary text-lg !py-4 !px-12 glow-primary"
            >
              ✨ Generate Reel
            </button>
            <p className="text-xs text-[var(--color-text-muted)] mt-3">
              Estimated time: ~90 seconds
            </p>
          </motion.div>
        )}

        {/* ── Job Progress ── */}
        <AnimatePresence>
          {isGenerating && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="glass-card p-8 mb-8"
            >
              <h3 className="text-xl font-bold mb-6 text-center">Creating Your Reel</h3>

              {/* Stage indicators */}
              <div className="flex items-center justify-between gap-2 mb-6 overflow-x-auto">
                {STAGES.filter(s => mode === "clone" || s.key !== "extracting_dna").map((stage, i) => {
                  const isActive = stage.key === currentStage;
                  const isPast = STAGES.findIndex(s => s.key === currentStage) > STAGES.findIndex(s => s.key === stage.key);

                  return (
                    <div key={stage.key} className="flex flex-col items-center min-w-[60px]">
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition-all ${
                          isActive
                            ? "gradient-bg glow-primary animate-pulse"
                            : isPast
                            ? "bg-[var(--color-success)]/20 text-[var(--color-success)]"
                            : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]"
                        }`}
                      >
                        {isPast ? "✓" : stage.icon}
                      </div>
                      <span className={`text-xs mt-1 ${isActive ? "text-white font-medium" : "text-[var(--color-text-muted)]"}`}>
                        {stage.label}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Progress bar */}
              <div className="progress-bar">
                <motion.div
                  className="progress-bar-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <p className="text-center text-sm text-[var(--color-text-muted)] mt-3">
                {progress}% complete
              </p>
              {/* DNA Visualizer */}
              {jobData?.style_dna && currentStage === "extracting_dna" && (
                 <div className="mt-8">
                   <DNAVisualizer dna={jobData.style_dna} />
                 </div>
              )}

              {/* Shot Director (Blueprint) */}
              {jobData?.blueprint && (currentStage === "generating_blueprint" || currentStage === "assembling") && (
                 <div className="mt-8 text-left">
                   <ShotDirector 
                      shots={jobData.blueprint.slots.map((s: any) => ({
                         shot_number: s.slot_id,
                         duration_seconds: s.end - s.start,
                         title: `Shot ${s.slot_id} (${s.type})`,
                         what_to_film: s.mood_role || "Video Segment",
                         how_to_film_it: s.ken_burns ? "Subtle motion" : "Static shot",
                         why_it_matters: "Builds momentum",
                         common_mistake: "Unsteady camera"
                      }))}
                   />
                 </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Reel Output ── */}
        <AnimatePresence>
          {reelReady && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-card p-8"
            >
              <div className="flex items-center gap-3 mb-6">
                <span className="text-3xl">✅</span>
                <div>
                  <h3 className="text-xl font-bold">Your Reel is Ready!</h3>
                  <p className="text-sm text-[var(--color-text-secondary)]">Export-ready for Instagram, TikTok, YouTube Shorts</p>
                </div>
              </div>

              {/* Preview Placeholder or Real Player */}
              <div className="aspect-[9/16] max-w-xs mx-auto bg-black rounded-2xl mb-6 flex items-center justify-center border border-[var(--color-border)] overflow-hidden">
                {reelData?.r2_key ? (
                  <ReelPlayer 
                    src={`/api/v1/reels/${reelData.id}/stream`} 
                    autoPlay={true}
                  />
                ) : (
                  <div className="text-center">
                    <span className="text-5xl block mb-3">🎬</span>
                    <p className="text-sm text-[var(--color-text-muted)]">Reel Preview</p>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      {reelData?.duration_ms ? `${Math.round(reelData.duration_ms / 1000)}s` : '15s'} · 1080x1920
                    </p>
                  </div>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex flex-wrap gap-3 justify-center mb-6">
                <button className="btn-primary">
                  📥 Download 9:16
                </button>
                <button className="btn-secondary">
                  📐 Download 1:1
                </button>
                <button className="btn-secondary">
                  🖥️ Download 16:9
                </button>
              </div>

              <div className="flex flex-wrap gap-3 justify-center">
                <button className="btn-secondary !text-sm">🔄 Regenerate</button>
                <button className="btn-secondary !text-sm">🔗 Share</button>
                <button className="btn-secondary !text-sm">📋 Copy Caption</button>
                <button className="btn-secondary !text-sm"># Copy Hashtags</button>
              </div>

              {/* Generated caption */}
              {reelData?.captions && (
                <div className="mt-6 p-4 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)]">
                  <h4 className="text-sm font-medium mb-2">Generated Caption</h4>
                  <p className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap">
                    {reelData.captions.text}
                  </p>
                  {reelData.captions.hashtags && (
                    <p className="text-sm text-[var(--color-primary-light)] mt-2">
                       {reelData.captions.hashtags.join(' ')}
                    </p>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
