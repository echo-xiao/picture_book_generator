"use client";

import { useState, useEffect } from "react";
import { getChapters } from "@/lib/api";
import type { PictureBook } from "@/types";

interface Props {
  bookId: string;
  onComplete: (book: PictureBook) => void;
  onBack: () => void;
}

const STEPS = [
  { label: "Extracting Text", detail: "Splitting book into chapters..." },
  { label: "Identifying Characters", detail: "AI reading the story to find all characters and aliases..." },
  { label: "Replacing Aliases", detail: "Standardizing character names in text..." },
  { label: "Segmenting Scenes", detail: "Splitting chapters into visual scenes..." },
  { label: "Annotating Scenes", detail: "AI identifying characters, actions, backgrounds per scene..." },
  { label: "Saving to Database", detail: "Storing results in MongoDB..." },
];

export function GenerationProgress({ bookId, onComplete, onBack }: Props) {
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  // Poll for preprocess completion
  useEffect(() => {
    let timer: NodeJS.Timeout;
    let elapsedTimer: NodeJS.Timeout;

    // Update elapsed time
    elapsedTimer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    // Estimate current step from elapsed time
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
    }, 15000);

    // Poll for completion
    async function poll() {
      try {
        const data = await getChapters(bookId);
        if (data.chapters && Object.keys(data.chapters).length > 0) {
          setDone(true);
          clearInterval(stepInterval);
          clearInterval(elapsedTimer);
          // Redirect to editor
          setTimeout(() => {
            window.location.href = `/editor/${bookId}`;
          }, 1500);
          return;
        }
      } catch {
        // Not ready yet, keep polling
      }
      timer = setTimeout(poll, 5000);
    }

    // Start polling after a delay (give preprocess time to start)
    timer = setTimeout(poll, 10000);

    return () => {
      clearTimeout(timer);
      clearInterval(stepInterval);
      clearInterval(elapsedTimer);
    };
  }, [bookId]);

  const progress = done ? 100 : Math.min(95, (currentStep / STEPS.length) * 100 + elapsed * 0.3);
  const step = STEPS[currentStep] || STEPS[STEPS.length - 1];

  return (
    <div className="animate-fade-in max-w-2xl mx-auto py-12">
      <div className="card text-center space-y-8">
        {/* Icon */}
        <div className="animate-float">
          <span className="text-6xl">{done ? "🎉" : "📖"}</span>
        </div>

        {/* Status */}
        <div>
          <h2 className="font-display text-2xl font-bold text-gray-800">
            {done ? "Preprocessing Complete!" : "Preprocessing Book..."}
          </h2>
          <p className="text-gray-500 mt-2">
            {done ? "Redirecting to editor..." : step.detail}
          </p>
          <p className="text-sm text-coral mt-1 font-semibold">
            {done ? "" : step.label}
          </p>
        </div>

        {/* Progress bar */}
        <div className="w-full">
          <div className="w-full h-4 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-coral to-sunshine rounded-full transition-all duration-700"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-400 mt-2">
            {done ? "100%" : `${Math.round(progress)}%`} — {Math.floor(elapsed / 60)}:{(elapsed % 60).toString().padStart(2, "0")}
          </p>
        </div>

        {/* Step indicators */}
        <div className="grid grid-cols-3 gap-3 text-left">
          {STEPS.map((s, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-2 text-xs ${
                idx < currentStep ? "text-gray-400" :
                idx === currentStep ? "text-coral font-semibold" :
                "text-gray-300"
              }`}
            >
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                idx < currentStep ? "bg-sage text-white" :
                idx === currentStep ? "bg-coral text-white" :
                "bg-gray-200"
              }`}>
                {idx < currentStep ? "✓" : idx + 1}
              </span>
              {s.label}
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-xl">
            <p className="font-semibold">Error</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        )}

        <button onClick={onBack} className="text-sm text-gray-400 hover:text-gray-600">
          Cancel
        </button>
      </div>
    </div>
  );
}
