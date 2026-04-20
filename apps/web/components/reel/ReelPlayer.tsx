"use client";

import { useEffect, useRef } from "react";

interface ReelPlayerProps {
  src: string;
  poster?: string;
  autoPlay?: boolean;
}

export function ReelPlayer({ src, poster, autoPlay = false }: ReelPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;

    video.src = src;
    video.load();

    if (autoPlay) {
      // Wait until the browser has enough metadata before attempting play,
      // otherwise we get an AbortError on slow connections.
      const onCanPlay = () => {
        video.play().catch((e) => {
          // Auto-play is blocked by browser policy on some devices — that's OK.
          console.log("Auto-play prevented:", e);
        });
      };
      video.addEventListener("canplay", onCanPlay, { once: true });
      return () => video.removeEventListener("canplay", onCanPlay);
    }
  }, [src, autoPlay]);

  return (
    <div className="relative w-full aspect-[9/16] bg-black rounded-xl overflow-hidden shadow-xl ring-1 ring-white/10">
      <video
        ref={videoRef}
        poster={poster}
        controls
        playsInline
        muted={autoPlay} // muted is required for autoplay to work in most browsers
        className="w-full h-full object-cover"
      />
    </div>
  );
}
