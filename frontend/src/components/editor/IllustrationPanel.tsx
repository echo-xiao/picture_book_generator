import { RefreshCw, Image, BookOpen } from "lucide-react";
import type { Segment } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface IllustrationPanelProps {
  selectedSegment: Segment;
  regenerating: boolean;
  onRegenerate: () => void;
}

export default function IllustrationPanel({
  selectedSegment,
  regenerating,
  onRegenerate,
}: IllustrationPanelProps) {
  return (
    <div className="w-[40%] shrink-0 overflow-y-auto p-3 border-r border-peach/20">
      <div className="card !p-3 mb-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-display font-bold text-gray-700 text-sm flex items-center gap-1">
            <Image size={14} /> Illustration
          </h3>
          <button
            onClick={onRegenerate}
            disabled={regenerating}
            className="btn-primary text-[10px] !px-2 !py-1 flex items-center gap-1"
          >
            <RefreshCw size={10} className={regenerating ? "animate-spin" : ""} />
            {regenerating ? "Generating..." : "Regenerate"}
          </button>
        </div>
        {regenerating ? (
          <div className="w-full aspect-square bg-peach/10 rounded-xl flex flex-col items-center justify-center gap-3">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-coral" />
            <p className="text-sm font-semibold text-gray-600">Generating illustration...</p>
            <p className="text-xs text-gray-400">This usually takes 30-60 seconds</p>
          </div>
        ) : selectedSegment.illustration_url ? (
          <img
            key={`${selectedSegment.id}`}
            src={`${API_BASE}${selectedSegment.illustration_url}?t=${Date.now()}`}
            alt="Page illustration"
            className="w-full rounded-xl shadow-md"
          />
        ) : (
          <div className="w-full aspect-square bg-peach/20 rounded-xl flex flex-col items-center justify-center text-gray-400 gap-2">
            <Image size={24} />
            <p className="text-xs">Click "Regenerate" to create</p>
          </div>
        )}
      </div>

      {/* Original Text (under illustration, full content) */}
      <div className="card !p-3 mb-3">
        <h3 className="font-display font-bold text-gray-700 mb-2 text-xs flex items-center gap-1">
          <BookOpen size={12} /> Original Text
        </h3>
        <div className="text-xs text-gray-600 bg-cream/50 rounded-lg p-3 !leading-[1.26]">
          {selectedSegment.text.split(/\n\n+/).map((para, i) => (
            <p key={i} className={i > 0 ? "mt-2" : ""}>{para.replace(/\n/g, " ").trim()}</p>
          ))}
        </div>
      </div>
    </div>
  );
}
