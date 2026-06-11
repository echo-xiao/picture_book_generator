import { Image as ImageIcon, RefreshCw } from "lucide-react";
import type { CharacterInfo, Segment } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export type SpecialPage = {
  type: string;
  label: string;
  url: string | null;
  chapter?: number;
  chapter_title?: string;
  chapter_summary?: string;
};

interface Props {
  special: SpecialPage;
  meta: { title?: string };
  bookId: string;
  characters: CharacterInfo[];
  sheets: Record<string, string>;
  segments: Segment[];
  specialCacheBust: number;
  regenSpecial: boolean;
  onRegenerate: () => void;
  canGenerate?: boolean;
}

export default function SpecialPageView({
  special,
  meta,
  bookId,
  characters,
  sheets,
  segments,
  specialCacheBust,
  regenSpecial,
  onRegenerate,
  canGenerate = true,
}: Props) {
  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Image */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col items-center justify-center">
        <h2 className="font-display text-lg font-bold text-gray-800 mb-4">{special.label}</h2>
        {special.url ? (
          <img
            src={`${API_BASE}${special.url}${
              specialCacheBust ? `${special.url.includes("?") ? "&" : "?"}v=${specialCacheBust}` : ""
            }`}
            alt={special.label}
            className="max-h-[calc(100vh-200px)] max-w-full rounded-xl shadow-md object-contain"
          />
        ) : regenSpecial ? (
          <div className="w-full max-w-md aspect-square bg-peach/10 rounded-xl flex flex-col items-center justify-center gap-3">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-coral" />
            <p className="text-sm text-gray-500">Generating...</p>
            <p className="text-xs text-gray-400">~30 seconds</p>
          </div>
        ) : (
          <div className="w-full max-w-md aspect-square bg-peach/20 rounded-xl flex flex-col items-center justify-center text-gray-400 gap-2">
            <ImageIcon size={32} />
            <p className="text-xs">Not generated yet</p>
          </div>
        )}
      </div>
      {/* Right: Info + Regenerate */}
      <div className="w-[300px] shrink-0 overflow-y-auto p-5 space-y-4 border-l border-peach/20">
        {/* Book Cover fields */}
        {special.type === "book_cover" && (
          <>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Book Title</label>
              <p className="text-sm text-gray-800 font-bold bg-cream/50 rounded-lg p-3">{meta.title || bookId}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Subtitle</label>
              <p className="text-sm text-gray-700 bg-cream/50 rounded-lg p-3">A Picture Book</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Main Characters</label>
              <div className="space-y-1">
                {characters.filter(c => c.role === "main").map(c => (
                  <div key={c.canonical_name} className="flex items-center gap-2 bg-cream/50 rounded-lg px-3 py-1.5">
                    <span className={`w-2 h-2 rounded-full ${sheets[c.canonical_name] ? "bg-green-400" : "bg-gray-300"}`} />
                    <span className="text-xs text-gray-700">{c.canonical_name}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Chapter Cover fields */}
        {special.type === "chapter_cover" && (
          <>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Chapter {(special.chapter ?? 0) + 1}</label>
              <p className="text-sm text-gray-800 font-bold bg-cream/50 rounded-lg p-3">{special.chapter_title || "Untitled"}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Chapter Summary</label>
              <p className="text-sm text-gray-700 bg-cream/50 rounded-lg p-3">{special.chapter_summary || "No summary yet. Run preprocess to generate."}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Characters in Chapter</label>
              <div className="flex flex-wrap gap-1.5">
                {(() => {
                  const charSet = new Set<string>();
                  segments.forEach(s => s.characters_in_scene?.forEach((c: string) => charSet.add(c)));
                  return Array.from(charSet).slice(0, 8).map(name => (
                    <span key={name} className="px-2 py-0.5 bg-sage/30 text-[10px] rounded-full text-gray-700">{name}</span>
                  ));
                })()}
              </div>
            </div>
          </>
        )}

        {/* Back Cover fields */}
        {special.type === "back_cover" && (
          <>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Book Title</label>
              <p className="text-sm text-gray-800 font-bold bg-cream/50 rounded-lg p-3">{meta.title || bookId}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Closing Text</label>
              <p className="text-sm text-gray-700 bg-cream/50 rounded-lg p-3">The End<br/>Thank you for reading!</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Style Reference</label>
              <p className="text-xs text-gray-500">Uses Book Cover as style reference for consistency</p>
            </div>
          </>
        )}

        <button
          onClick={onRegenerate}
          disabled={regenSpecial || !canGenerate}
          className="btn-primary text-sm !px-4 !py-2 flex items-center gap-1.5 w-full justify-center"
        >
          <RefreshCw size={14} className={regenSpecial ? "animate-spin" : ""} />
          {regenSpecial ? "Generating..." : special.url ? "Regenerate" : "Generate"}
        </button>
      </div>
    </div>
  );
}
