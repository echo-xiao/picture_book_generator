"use client";

import { useState } from "react";
import { Users, RefreshCw, Save, ChevronDown, ChevronUp } from "lucide-react";
import { updateCharacter, regenerateCharacterSheet, getCharacters } from "@/lib/api";
import type { CharacterInfo } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CharacterManagementProps {
  bookId: string;
  characters: CharacterInfo[];
  sheets: Record<string, string>;
  aliasMap: Record<string, string>;
  onCharactersUpdate: (characters: CharacterInfo[], sheets: Record<string, string>) => void;
}

export default function CharacterManagement({
  bookId,
  characters,
  sheets,
  aliasMap,
  onCharactersUpdate,
}: CharacterManagementProps) {
  const [expandedChar, setExpandedChar] = useState<string | null>(null);
  const [editingChar, setEditingChar] = useState<Record<string, any>>({});
  const [savingChar, setSavingChar] = useState<string | null>(null);
  const [regenChar, setRegenChar] = useState<string | null>(null);

  const startEdit = (char: CharacterInfo) => {
    setEditingChar({
      canonical_name: char.canonical_name,
      gender: char.gender || "unknown",
      role: char.role || "supporting",
      appearance: char.appearance || "",
      description: char.description || "",
      aliases: Object.entries(aliasMap)
        .filter(([, v]) => v === char.canonical_name)
        .map(([k]) => k),
    });
    setExpandedChar(char.canonical_name);
  };

  const handleSave = async (charName: string) => {
    setSavingChar(charName);
    try {
      await updateCharacter(bookId, charName, editingChar);
      const data = await getCharacters(bookId);
      onCharactersUpdate(data.characters || [], data.sheets || {});
    } catch (e) {
      console.error("Save character failed:", e);
    } finally {
      setSavingChar(null);
    }
  };

  const handleRegenSheet = async (charName: string) => {
    setRegenChar(charName);
    try {
      await regenerateCharacterSheet(bookId, charName);
      setTimeout(async () => {
        const data = await getCharacters(bookId);
        onCharactersUpdate(data.characters || [], data.sheets || {});
        setRegenChar(null);
      }, 30000);
    } catch (e) {
      console.error("Regen sheet failed:", e);
      setRegenChar(null);
    }
  };

  const mainChars = characters.filter(c => c.role === "main");
  const supportChars = characters.filter(c => c.role === "supporting");
  const minorChars = characters.filter(c => c.role !== "main" && c.role !== "supporting");

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="font-display text-xl font-bold text-gray-800 mb-1 flex items-center gap-2">
          <Users size={20} /> Character Management
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          Review and edit characters before generating illustrations. Changes affect all segments.
        </p>

        {/* Main Characters */}
        {mainChars.length > 0 && (
          <Section title={`Main Characters (${mainChars.length})`}>
            {mainChars.map(char => (
              <CharRow
                key={char.canonical_name}
                char={char}
                sheetUrl={sheets[char.canonical_name]}
                expanded={expandedChar === char.canonical_name}
                editing={editingChar}
                saving={savingChar === char.canonical_name}
                regenning={regenChar === char.canonical_name}
                onToggle={() => expandedChar === char.canonical_name ? setExpandedChar(null) : startEdit(char)}
                onFieldChange={(field, value) => setEditingChar(prev => ({ ...prev, [field]: value }))}
                onSave={() => handleSave(char.canonical_name)}
                onRegenSheet={() => handleRegenSheet(char.canonical_name)}
              />
            ))}
          </Section>
        )}

        {/* Supporting Characters */}
        {supportChars.length > 0 && (
          <Section title={`Supporting Characters (${supportChars.length})`}>
            {supportChars.map(char => (
              <CharRow
                key={char.canonical_name}
                char={char}
                sheetUrl={sheets[char.canonical_name]}
                expanded={expandedChar === char.canonical_name}
                editing={editingChar}
                saving={savingChar === char.canonical_name}
                regenning={regenChar === char.canonical_name}
                onToggle={() => expandedChar === char.canonical_name ? setExpandedChar(null) : startEdit(char)}
                onFieldChange={(field, value) => setEditingChar(prev => ({ ...prev, [field]: value }))}
                onSave={() => handleSave(char.canonical_name)}
                onRegenSheet={() => handleRegenSheet(char.canonical_name)}
              />
            ))}
          </Section>
        )}

        {/* Minor Characters */}
        {minorChars.length > 0 && (
          <Section title={`Minor Characters (${minorChars.length})`}>
            {minorChars.map(char => (
              <CharRow
                key={char.canonical_name}
                char={char}
                sheetUrl={sheets[char.canonical_name]}
                expanded={expandedChar === char.canonical_name}
                editing={editingChar}
                saving={savingChar === char.canonical_name}
                regenning={regenChar === char.canonical_name}
                onToggle={() => expandedChar === char.canonical_name ? setExpandedChar(null) : startEdit(char)}
                onFieldChange={(field, value) => setEditingChar(prev => ({ ...prev, [field]: value }))}
                onSave={() => handleSave(char.canonical_name)}
                onRegenSheet={() => handleRegenSheet(char.canonical_name)}
              />
            ))}
          </Section>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <h3 className="text-sm font-bold text-gray-600 mb-3 border-b border-peach/30 pb-2">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function CharRow({
  char,
  sheetUrl,
  expanded,
  editing,
  saving,
  regenning,
  onToggle,
  onFieldChange,
  onSave,
  onRegenSheet,
}: {
  char: CharacterInfo;
  sheetUrl?: string;
  expanded: boolean;
  editing: Record<string, any>;
  saving: boolean;
  regenning: boolean;
  onToggle: () => void;
  onFieldChange: (field: string, value: any) => void;
  onSave: () => void;
  onRegenSheet: () => void;
}) {
  return (
    <div className="card !p-4">
      {/* Collapsed: left text + right image */}
      <button onClick={onToggle} className="w-full flex items-center gap-4 text-left">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-bold text-gray-800">{char.canonical_name}</span>
            <span className="text-[10px] px-1.5 py-0.5 bg-sage/30 rounded text-gray-600">
              {char.gender || "?"} / {char.role || "?"}
            </span>
          </div>
          {char.description && (
            <p className="text-xs text-gray-500 mb-1">{char.description}</p>
          )}
          {char.appearance && (
            <p className="text-xs text-gray-400 italic">{char.appearance.slice(0, 120)}{char.appearance.length > 120 ? "..." : ""}</p>
          )}
        </div>
        {sheetUrl ? (
          <img
            src={`${API_BASE}${sheetUrl}`}
            alt={char.canonical_name}
            className="w-20 h-20 rounded-lg object-cover shrink-0"
          />
        ) : (
          <div className="w-20 h-20 bg-peach/20 rounded-lg flex items-center justify-center shrink-0">
            <Users size={20} className="text-gray-300" />
          </div>
        )}
        {expanded ? <ChevronUp size={16} className="text-gray-400 shrink-0" /> : <ChevronDown size={16} className="text-gray-400 shrink-0" />}
      </button>

      {/* Expanded: edit form */}
      {expanded && (
        <div className="mt-4 border-t border-peach/20 pt-4">
          <div className="flex gap-6">
            {/* Left: form fields */}
            <div className="flex-1 space-y-3">
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="text-xs text-gray-500 font-semibold mb-1 block">Gender</label>
                  <select
                    value={editing.gender || "unknown"}
                    onChange={e => onFieldChange("gender", e.target.value)}
                    className="w-full rounded-lg border border-peach/50 px-3 py-2 text-sm bg-white"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-500 font-semibold mb-1 block">Role</label>
                  <select
                    value={editing.role || "supporting"}
                    onChange={e => onFieldChange("role", e.target.value)}
                    className="w-full rounded-lg border border-peach/50 px-3 py-2 text-sm bg-white"
                  >
                    <option value="main">Main</option>
                    <option value="supporting">Supporting</option>
                    <option value="minor">Minor</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs text-gray-500 font-semibold mb-1 block">Appearance</label>
                <textarea
                  value={editing.appearance || ""}
                  onChange={e => onFieldChange("appearance", e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-peach/50 px-3 py-2 text-sm resize-none"
                  placeholder="Physical description: hair, face, clothing, accessories..."
                />
              </div>

              <div>
                <label className="text-xs text-gray-500 font-semibold mb-1 block">Description</label>
                <textarea
                  value={editing.description || ""}
                  onChange={e => onFieldChange("description", e.target.value)}
                  rows={2}
                  className="w-full rounded-lg border border-peach/50 px-3 py-2 text-sm resize-none"
                  placeholder="Character background and personality..."
                />
              </div>

              <div className="flex gap-2 pt-1">
                <button onClick={onSave} disabled={saving} className="btn-primary text-xs !px-3 !py-1.5 flex items-center gap-1">
                  <Save size={12} />
                  {saving ? "Saving..." : "Save Changes"}
                </button>
                <button onClick={onRegenSheet} disabled={regenning} className="btn-secondary text-xs !px-3 !py-1.5 flex items-center gap-1">
                  <RefreshCw size={12} className={regenning ? "animate-spin" : ""} />
                  {regenning ? "Generating..." : "Regenerate Sheet"}
                </button>
              </div>
            </div>

            {/* Right: character sheet image */}
            <div className="w-48 shrink-0">
              <label className="text-xs text-gray-500 font-semibold mb-1 block">Character Sheet</label>
              {sheetUrl ? (
                <img
                  src={`${API_BASE}${sheetUrl}`}
                  alt={char.canonical_name}
                  className="w-full rounded-lg shadow-md"
                />
              ) : (
                <div className="w-full aspect-square bg-peach/20 rounded-lg flex flex-col items-center justify-center text-gray-400 gap-2">
                  <Users size={24} />
                  <p className="text-[10px]">No sheet yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
