"use client";

import { Video, Info, AlertTriangle, PlayCircle } from "lucide-react";
import { motion } from "framer-motion";

interface ShotInstruction {
  shot_number: int;
  duration_seconds: int;
  title: string;
  what_to_film: string;
  how_to_film_it: string;
  why_it_matters: string;
  common_mistake: string;
}

interface ShotDirectorProps {
  shots: ShotInstruction[];
}

export function ShotDirector({ shots }: ShotDirectorProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
          <Video className="w-7 h-7 text-blue-500" />
          AI Shot Director
        </h2>
        <span className="px-4 py-1.5 rounded-full bg-blue-500/10 text-blue-400 font-medium text-sm border border-blue-500/20">
          {shots.length} Shots Required
        </span>
      </div>

      <div className="space-y-4">
        {shots.map((shot, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: idx * 0.1 }}
            className="group block relative rounded-2xl border border-gray-800 bg-gray-900 overflow-hidden hover:border-blue-500/50 hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300"
          >
            <div className="absolute top-0 left-0 w-1.5 h-full bg-blue-500/50 group-hover:bg-blue-500 transition-colors" />
            
            <div className="p-6 sm:p-8 pl-8 sm:pl-10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold">
                    {shot.shot_number}
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white mb-1">{shot.title}</h3>
                    <p className="text-gray-400 text-sm flex items-center gap-2">
                      <PlayCircle className="w-4 h-4" />
                      {shot.duration_seconds} seconds
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-800/80 hover:bg-gray-800 transition-colors">
                    <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-widest mb-2 flex items-center gap-2">
                      <Video className="w-4 h-4 text-blue-400" /> What to Film
                    </h4>
                    <p className="text-gray-100">{shot.what_to_film}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-800/80 hover:bg-gray-800 transition-colors">
                    <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-widest mb-2 flex items-center gap-2">
                      <PlayCircle className="w-4 h-4 text-pink-400" /> How to Film It
                    </h4>
                    <p className="text-gray-100">{shot.how_to_film_it}</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-800/80 hover:bg-gray-800 transition-colors">
                    <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-widest mb-2 flex items-center gap-2">
                      <Info className="w-4 h-4 text-green-400" /> Why It Matters
                    </h4>
                    <p className="text-gray-400 text-sm">{shot.why_it_matters}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 transition-colors">
                    <h4 className="text-sm font-semibold text-red-400 uppercase tracking-widest mb-2 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" /> Common Mistake
                    </h4>
                    <p className="text-red-200/80 text-sm">{shot.common_mistake}</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
