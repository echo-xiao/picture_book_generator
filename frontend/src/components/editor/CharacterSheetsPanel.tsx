import type { Segment, CharacterInfo } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CharacterSheetsPanelProps {
  selectedSegment: Segment;
  characters: CharacterInfo[];
  sheets: Record<string, string>;
  bookId: string;
  onRegenerateSheet: (canonicalName: string) => void;
}

export default function CharacterSheetsPanel({
  selectedSegment,
  characters,
  sheets,
  onRegenerateSheet,
}: CharacterSheetsPanelProps) {
  const filteredCharacters = characters.filter((c) => {
    if (!sheets[c.canonical_name]) return false;
    const sceneChars = selectedSegment?.characters_in_scene || [];
    if (sceneChars.length === 0) return false;
    const cName = c.canonical_name.toLowerCase();
    const cParts = cName.split(/\s+/).filter((p) => p.length > 3);
    return sceneChars.some((sc) => {
      const scLower = sc.toLowerCase();
      if (cName === scLower) return true;
      const scParts = scLower.split(/\s+/).filter((p) => p.length > 3);
      return cParts.some((p) => scLower.includes(p)) || scParts.some((p) => cName.includes(p));
    });
  });

  return (
    <div className="w-1/2 overflow-y-auto p-3">
      <div className="card !p-3">
        <h3 className="font-display font-bold text-gray-700 text-xs mb-3">Character Sheets</h3>
        <div className="space-y-4">
          {filteredCharacters.map((char) => {
            const sheetUrl = sheets[char.canonical_name];

            return (
              <div key={char.canonical_name} className="border border-peach/30 rounded-xl p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-gray-700">
                    {char.canonical_name}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 bg-sage/30 rounded text-gray-600">
                    {char.gender} / {char.role}
                  </span>
                </div>
                {sheetUrl ? (
                  <img
                    src={`${API_BASE}${sheetUrl}`}
                    alt={char.canonical_name}
                    className="w-full rounded-lg mb-2"
                  />
                ) : (
                  <div className="w-full h-24 bg-peach/20 rounded-lg flex items-center justify-center text-xs text-gray-400 mb-2">
                    No sheet
                  </div>
                )}
                <p className="text-[10px] text-gray-500 mb-2">{char.description}</p>
                <button
                  onClick={() => onRegenerateSheet(char.canonical_name)}
                  className="text-xs text-coral hover:text-coral/80 font-semibold"
                >
                  Regenerate Sheet
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
