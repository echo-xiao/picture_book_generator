import type { Segment, CharacterInfo } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CharacterSheetsPanelProps {
  selectedSegment: Segment;
  characters: CharacterInfo[];
  sheets: Record<string, string>;
  portraits: Record<string, string>;
  bookId: string;
  onRegenerateSheet: (canonicalName: string) => void;
  onNavigateToCharacter?: (charName: string) => void;
}

export default function CharacterSheetsPanel({
  selectedSegment,
  characters,
  sheets,
  onNavigateToCharacter,
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
        <h3 className="font-display font-bold text-gray-700 text-xs mb-3">Characters in Scene</h3>
        <div className="space-y-4">
          {filteredCharacters.map((char) => {
            const sheetUrl = sheets[char.canonical_name];
            return (
              <div
                key={char.canonical_name}
                className="cursor-pointer hover:opacity-80 transition-opacity"
                onClick={() => onNavigateToCharacter?.(char.canonical_name)}
              >
                <img
                  src={`${API_BASE}${sheetUrl}?t=${Date.now()}`}
                  alt={char.canonical_name}
                  className="w-full rounded-xl mb-2"
                />
                <p className="text-xs font-bold text-gray-800">{char.canonical_name}</p>
                <p className="text-[10px] text-gray-500">{char.gender} / {char.role}</p>
              </div>
            );
          })}
          {filteredCharacters.length === 0 && (
            <p className="text-[10px] text-gray-400">No matching characters.</p>
          )}
        </div>
      </div>
    </div>
  );
}
