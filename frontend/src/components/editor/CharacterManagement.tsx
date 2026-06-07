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
      // Poll for new sheet (takes ~30s)
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
  const supportChars = characters.filter(c => c.role !== "main");

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h2 className="font-display text-xl font-bold text-gray-800 mb-1 flex items-center gap-2">
          <Users size={20} /> Character Management
        </h2>
        <p className="text-xs text-gray-500 mb-6">
          Review and edit characters before generating illustrations. Changes here affect all segments.
        </p>

        {/* Main Characters */}
        {mainChars.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-bold text-gray-600 mb-3">Main Characters ({mainChars.length})</h3>
            <div className="grid grid-cols-2 gap-4">
              {mainChars.map(char => (
                <CharCard
                  key={char.canonical_name}
                  char={char}
                  sheetUrl={sheets[char.canonical_name]}
                  expanded={expandedChar === char.canonical_name}
                  editing={editingChar}
                  saving={savingChar === char.canonical_name}
                  regenning={regenChar === char.canonical_name}
                  onToggle={() => {
                    if (expandedChar === char.canonical_name) {
                      setExpandedChar(null);
                    } else {
                      startEdit(char);
                    }
                  }}
                  onFieldChange={(field, value) => setEditingChar(prev => ({ ...prev, [field]: value }))}
                  onSave={() => handleSave(char.canonical_name)}
                  onRegenSheet={() => handleRegenSheet(char.canonical_name)}
                  bookId={bookId}
                />
              ))}
            </div>
          </div>
        )}

        {/* Supporting Characters */}
        {supportChars.length > 0 && (
          <div>
            <h3 className="text-sm font-bold text-gray-600 mb-3">Supporting Characters ({supportChars.length})</h3>
            <div className="grid grid-cols-3 gap-3">
              {supportChars.map(char => (
                <CharCard
                  key={char.canonical_name}
                  char={char}
                  sheetUrl={sheets[char.canonical_name]}
                  expanded={expandedChar === char.canonical_name}
                  editing={editingChar}
                  saving={savingChar === char.canonical_name}
                  regenning={regenChar === char.canonical_name}
                  onToggle={() => {
                    if (expandedChar === char.canonical_name) {
                      setExpandedChar(null);
                    } else {
                      startEdit(char);
                    }
                  }}
                  onFieldChange={(field, value) => setEditingChar(prev => ({ ...prev, [field]: value }))}
                  onSave={() => handleSave(char.canonical_name)}
                  onRegenSheet={() => handleRegenSheet(char.canonical_name)}
                  bookId={bookId}
                  compact
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CharCard({
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
  bookId,
  compact = false,
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
  bookId: string;
  compact?: boolean;
}) {
  return (
    <div className="card !p-3">
      {/* Header */}
      <button onClick={onToggle} className="w-full flex items-center gap-3 text-left">
        {sheetUrl ? (
          <img
            src={`${API_BASE}${sheetUrl}`}
            alt={char.canonical_name}
            className={`${compact ? "w-12 h-12" : "w-16 h-16"} rounded-lg object-cover shrink-0`}
          />
        ) : (
          <div className={`${compact ? "w-12 h-12" : "w-16 h-16"} bg-peach/20 rounded-lg flex items-center justify-center shrink-0`}>
            <Users size={compact ? 16 : 20} className="text-gray-400" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className={`${compact ? "text-xs" : "text-sm"} font-bold text-gray-800 truncate`}>
            {char.canonical_name}
          </p>
          <p className="text-[10px] text-gray-500">
            {char.gender || "?"} / {char.role || "supporting"}
          </p>
          {!compact && char.description && (
            <p className="text-[10px] text-gray-400 truncate mt-0.5">{char.description}</p>
          )}
        </div>
        {expanded ? <ChevronUp size={14} className="text-gray-400 shrink-0" /> : <ChevronDown size={14} className="text-gray-400 shrink-0" />}
      </button>

      {/* Expanded Edit Form */}
      {expanded && (
        <div className="mt-3 space-y-2 border-t border-peach/20 pt-3">
          {/* Character Sheet */}
          {sheetUrl && (
            <div className="mb-2">
              <img
                src={`${API_BASE}${sheetUrl}`}
                alt={char.canonical_name}
                className="w-full rounded-lg"
              />
            </div>
          )}

          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-[10px] text-gray-500 font-semibold">Gender</label>
              <select
                value={editing.gender || "unknown"}
                onChange={e => onFieldChange("gender", e.target.value)}
                className="w-full rounded-md border border-peach/50 px-2 py-1 text-xs bg-white"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="text-[10px] text-gray-500 font-semibold">Role</label>
              <select
                value={editing.role || "supporting"}
                onChange={e => onFieldChange("role", e.target.value)}
                className="w-full rounded-md border border-peach/50 px-2 py-1 text-xs bg-white"
              >
                <option value="main">Main</option>
                <option value="supporting">Supporting</option>
                <option value="minor">Minor</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-[10px] text-gray-500 font-semibold">Appearance</label>
            <textarea
              value={editing.appearance || ""}
              onChange={e => onFieldChange("appearance", e.target.value)}
              rows={3}
              className="w-full rounded-md border border-peach/50 px-2 py-1.5 text-xs resize-none"
              placeholder="Physical description..."
            />
          </div>

          <div>
            <label className="text-[10px] text-gray-500 font-semibold">Description</label>
            <textarea
              value={editing.description || ""}
              onChange={e => onFieldChange("description", e.target.value)}
              rows={2}
              className="w-full rounded-md border border-peach/50 px-2 py-1.5 text-xs resize-none"
              placeholder="Character background..."
            />
          </div>

          <div className="flex gap-2 pt-1">
            <button
              onClick={onSave}
              disabled={saving}
              className="btn-primary text-[10px] !px-2.5 !py-1 flex items-center gap-1"
            >
              <Save size={10} />
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={onRegenSheet}
              disabled={regenning}
              className="btn-secondary text-[10px] !px-2.5 !py-1 flex items-center gap-1"
            >
              <RefreshCw size={10} className={regenning ? "animate-spin" : ""} />
              {regenning ? "Generating..." : "Regen Sheet"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
