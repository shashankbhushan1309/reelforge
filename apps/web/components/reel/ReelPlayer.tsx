"use client";

import { useEffect, useRef } from "react";
import Hls from "hls.js";

interface ReelPlayerProps {
  src: string;
  poster?: string;
  autoPlay?: boolean;
}

export function ReelPlayer({ src, poster, autoPlay = false }: ReelPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    let hls: Hls;

    if (src.endsWith(".m3u8") && Hls.isSupported()) {
      hls = new Hls({
        capLevelToPlayerSize: true,
        maxBufferLength: 30,
      });

      hls.loadSource(src);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (autoPlay) {
          video.play().catch((e) => console.log("Auto-play prevented", e));
        }
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // For Safari native HLS
      video.src = src;
      if (autoPlay) {
        video.play().catch((e) => console.log("Auto-play prevented", e));
      }
    } else {
      // Fallback for direct MP4
      video.src = src;
    }

    return () => {
      if (hls) {
        hls.destroy();
      }
    };
  }, [src, autoPlay]);

  return (
    <div className="relative w-full aspect-[9/16] bg-black rounded-xl overflow-hidden shadow-xl ring-1 ring-white/10">
      <video
        ref={videoRef}
        poster={poster}
        controls
        playsInline
        className="w-full h-full object-cover"
      />
    </div>
  );
}
