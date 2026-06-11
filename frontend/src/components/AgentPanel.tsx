"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const DEFAULT_CHAPTER =
  "Nick Carraway moved to a small house in West Egg, next door to a huge mansion. " +
  "One evening he drove to East Egg to have dinner with his cousin Daisy Buchanan and " +
  "her husband Tom. Daisy's friend Jordan Baker was there too. Across the bay, a " +
  "mysterious man named Gatsby stood alone on his lawn, reaching toward a green light.";

const BADGES = [
  "Google Agent Builder (ADK)",
  "Vertex AI Agent Engine",
  "Gemini 3.5 · Vertex",
  "MongoDB MCP",
];

interface PlanResult {
  character_brief?: string;
  pages?: string;
  illustration_prompts?: string;
  tool_calls?: string[];
  runtime?: string;
  model?: string;
  error?: string;
}

export function AgentPanel() {
  const [bookId, setBookId] = useState("the_great_gatsby");
  const [chapter, setChapter] = useState(DEFAULT_CHAPTER);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlanResult | null>(null);

  const run = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/adk/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ book_id: bookId, chapter_text: chapter }),
      });
      setResult(await res.json());
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="text-center mb-6">
        <h2 className="font-display text-2xl font-bold text-gray-800">AI Story Agent</h2>
        <p className="text-sm text-gray-500 mt-1">
          A multi-step agent built with Google&apos;s Agent Development Kit, running on
          Vertex AI Agent Engine
        </p>
        <div className="flex flex-wrap gap-2 justify-center mt-3">
          {BADGES.map((b) => (
            <span
              key={b}
              className="text-xs px-3 py-1 rounded-full bg-peach/50 text-gray-700 font-semibold"
            >
              {b}
            </span>
          ))}
        </div>
      </div>

      {/* pipeline */}
      <div className="flex items-center justify-center gap-2 text-center mb-6">
        {[
          ["📚 Analyzer", "reads cast from MongoDB"],
          ["✍️ Writer", "kid-friendly pages"],
          ["🎨 Art Director", "illustration prompts"],
        ].map(([t, s], i) => (
          <div key={t} className="flex items-center gap-2">
            <div className="px-3 py-2 rounded-xl bg-white border border-peach/40">
              <div className="text-sm font-semibold text-gray-800">{t}</div>
              <div className="text-[10px] text-gray-500">{s}</div>
            </div>
            {i < 2 && <span className="text-coral font-bold">→</span>}
          </div>
        ))}
      </div>

      {/* input */}
      <div className="bg-white rounded-2xl border border-peach/30 p-4 mb-4 shadow-sm">
        <label className="block text-xs font-semibold text-gray-600 mb-1">Book ID</label>
        <input
          value={bookId}
          onChange={(e) => setBookId(e.target.value)}
          className="w-full mb-3 px-3 py-2 rounded-lg border border-gray-200 text-sm"
        />
        <label className="block text-xs font-semibold text-gray-600 mb-1">Chapter text</label>
        <textarea
          value={chapter}
          onChange={(e) => setChapter(e.target.value)}
          rows={4}
          className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm resize-y"
        />
        <button
          onClick={run}
          disabled={loading}
          className="mt-3 w-full px-4 py-2 rounded-xl bg-coral text-white font-semibold shadow-md hover:opacity-90 transition disabled:opacity-50"
        >
          {loading
            ? "Agent is thinking… (first run may take ~1 min to warm up)"
            : "Run the Agent ✨"}
        </button>
      </div>

      {/* results */}
      {result?.error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
          {result.error}
        </div>
      )}
      {result && !result.error && (
        <div className="space-y-3">
          {result.tool_calls && result.tool_calls.length > 0 && (
            <div className="text-xs text-gray-500 text-center">
              🔧 tool calls: {result.tool_calls.join(", ")}
              {result.runtime ? ` · runtime: ${result.runtime}` : ""}
            </div>
          )}
          <ResultCard title="1 · Character Brief — read from MongoDB" body={result.character_brief} />
          <ResultCard title="2 · Picture-Book Pages — Writer" body={result.pages} />
          <ResultCard title="3 · Illustration Prompts — Art Director" body={result.illustration_prompts} />
        </div>
      )}
    </div>
  );
}

function ResultCard({ title, body }: { title: string; body?: string }) {
  if (!body) return null;
  return (
    <div className="bg-white rounded-2xl border border-peach/30 p-4 shadow-sm">
      <h3 className="font-display font-bold text-gray-800 mb-2">{title}</h3>
      <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
        {body}
      </pre>
    </div>
  );
}
