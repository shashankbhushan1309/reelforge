"use client";

import { Activity, Type, Palette, Move, Scissors } from "lucide-react";
import { motion } from "framer-motion";

interface DNAVisualizerProps {
  dna: {
    cut_pace: string;
    color_grade: string;
    transition_type: string;
    text_energy: string;
    bpm: number;
    visual_motion: string;
    color_temperature: string;
  };
}

export function DNAVisualizer({ dna }: DNAVisualizerProps) {
  const metrics = [
    {
      label: "Cut Pace",
      value: dna.cut_pace,
      icon: <Scissors className="w-5 h-5 text-blue-400" />,
      color: "bg-blue-500",
      score: dna.cut_pace === "fast" ? 90 : dna.cut_pace === "medium" ? 50 : 20,
    },
    {
      label: "BPM Energy",
      value: `${dna.bpm} BPM`,
      icon: <Activity className="w-5 h-5 text-pink-400" />,
      color: "bg-pink-500",
      score: Math.min((dna.bpm / 200) * 100, 100),
    },
    {
      label: "Text Energy",
      value: dna.text_energy,
      icon: <Type className="w-5 h-5 text-purple-400" />,
      color: "bg-purple-500",
      score: dna.text_energy === "high" ? 85 : dna.text_energy === "medium" ? 50 : 15,
    },
    {
      label: "Color Temp",
      value: dna.color_temperature,
      icon: <Palette className="w-5 h-5 text-amber-400" />,
      color: "bg-amber-500",
      score: dna.color_temperature === "warm" ? 80 : 30,
    },
    {
      label: "Visual Motion",
      value: dna.visual_motion,
      icon: <Move className="w-5 h-5 text-green-400" />,
      color: "bg-green-500",
      score: dna.visual_motion === "high" ? 90 : dna.visual_motion === "medium" ? 60 : 30,
    },
  ];

  return (
    <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 shadow-2xl">
      <div className="flex items-center justify-between mb-8">
        <h3 className="text-xl font-semibold text-white flex items-center gap-2">
          <Activity className="w-6 h-6 text-blue-500" />
          Style DNA Profile
        </h3>
        <div className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-sm font-medium border border-blue-500/20">
          Match Accuracy: 96%
        </div>
      </div>

      <div className="space-y-6">
        {metrics.map((metric, idx) => (
          <div key={idx} className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="flex items-center gap-2 text-gray-300">
                {metric.icon}
                {metric.label}
              </span>
              <span className="text-gray-100 font-medium uppercase tracking-wider text-xs">
                {metric.value}
              </span>
            </div>
            <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${metric.score}%` }}
                transition={{ duration: 1, delay: idx * 0.1, ease: "easeOut" }}
                className={`h-full ${metric.color} rounded-full`}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 pt-6 border-t border-gray-800 grid grid-cols-2 gap-4">
        <div className="bg-gray-800/50 p-4 rounded-xl">
          <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Color Grade</p>
          <p className="text-white font-medium capitalize">{dna.color_grade.replace("_", " ")}</p>
        </div>
        <div className="bg-gray-800/50 p-4 rounded-xl">
          <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Transitions</p>
          <p className="text-white font-medium capitalize">{dna.transition_type.replace("_", " ")}</p>
        </div>
      </div>
    </div>
  );
}
